"""零依赖语句覆盖率：只用标准库，量一量测试到底跑到了 mock_server.py 的多少行。

为什么不用 pytest-cov：这个项目坚持"不装包也能跑"（allure 还要装 Java）。
而标准库的 sys.settrace 足够回答一个关键问题：**哪些代码行从来没被执行过？**

原理：
  1. 用 compile() 把被测文件编译一遍，从字节码里拿到"可执行行"做分母；
  2. 打开 sys.settrace / threading.settrace，跑一遍接口场景，记录命中的行做分子；
  3. 两者相减就是"从没被测试碰过的代码"——那些就是风险区。

用法：
    python coverage_simple.py             # 打印覆盖率与未覆盖的行
    python coverage_simple.py --min 85    # 低于 85% 时退出码 1（给 CI 用）
"""

import argparse
import os
import sys
import threading
import types

TARGET = "mock_server.py"


def _lines_of(code):
    """递归收集一个代码对象（含它内部定义的函数）里所有可执行行号。"""
    lines = {lineno for _, _, lineno in code.co_lines() if lineno is not None}
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            lines |= _lines_of(const)
    return lines


def executable_lines(path):
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return _lines_of(compile(source, path, "exec"))


class Tracer:
    """只记录被测文件执行过的行。别的文件（requests、标准库）一概不看。"""

    def __init__(self, target):
        self.target = os.path.normcase(os.path.abspath(target))
        self.hit = set()

    def _same_file(self, filename):
        return os.path.normcase(os.path.abspath(filename)) == self.target

    def __call__(self, frame, event, arg):
        if event == "call":
            if not self._same_file(frame.f_code.co_filename):
                return None          # 不跟踪其他文件，也不跟踪它们的子帧
            self.hit.add(frame.f_lineno)
            return self
        if event == "line":
            self.hit.add(frame.f_lineno)
        return self

    def start(self):
        sys.settrace(self)
        threading.settrace(self)     # 被测服务跑在子线程里，这行不能少

    def stop(self):
        sys.settrace(None)
        threading.settrace(None)


def scenario(base_url):
    """把所有路由和主要错误分支都走一遍 —— 分子就靠它。"""
    import requests

    payload = {
        "firstname": "佳吉",
        "lastname": "刘",
        "totalprice": 288,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-10", "checkout": "2026-11-12"},
    }
    json_type = {"Content-Type": "application/json"}

    # 健康检查、首页、查询（含分页与库存）
    requests.get(f"{base_url}/")
    requests.get(f"{base_url}/ping")
    requests.get(f"{base_url}/booking")
    requests.get(f"{base_url}/booking/999")               # 查不到
    requests.get(f"{base_url}/no-such-route")             # 路由不存在
    requests.get(f"{base_url}/rooms")
    requests.get(f"{base_url}/booking?page=1&size=2")     # 分页信封
    requests.get(f"{base_url}/booking?roomtype=limited")  # 按房型过滤
    requests.get(f"{base_url}/booking?page=0")            # 非法页码
    requests.get(f"{base_url}/booking?size=999")          # 非法页大小
    requests.get(f"{base_url}/booking?page=abc&size=1")   # 非整数参数

    # 鉴权：错密码 / 对密码 / 两种携带 token 的方式
    requests.post(f"{base_url}/auth", json={"username": "admin", "password": "bad"})
    token = requests.post(
        f"{base_url}/auth", json={"username": "admin", "password": "password123"}
    ).json()["token"]
    bearer = {**json_type, "Authorization": f"Bearer {token}"}
    cookie = {**json_type, "Cookie": f"token={token}"}

    # 只读账号：能查、不能写（403 需要 admin 权限）
    viewer = requests.post(
        f"{base_url}/auth", json={"username": "viewer", "password": "viewer123"}
    ).json()["token"]
    viewer_headers = {**json_type, "Authorization": f"Bearer {viewer}"}
    requests.get(f"{base_url}/booking", headers=viewer_headers)
    requests.post(f"{base_url}/booking", json=payload, headers=viewer_headers)
    requests.delete(f"{base_url}/booking/1", headers=viewer_headers)

    # 创建：没带 token / 坏 JSON / 不是对象 / 各种校验失败 / 成功
    requests.post(f"{base_url}/booking", json=payload)
    requests.post(f"{base_url}/booking", data="{不是 JSON", headers=bearer)
    requests.post(f"{base_url}/booking", json=[], headers=bearer)
    for bad_body in (
        {},
        {**payload, "bookingdates": {}},
        {**payload, "bookingdates": {"checkin": "2026/11/10", "checkout": "2026-11-12"}},
        {**payload, "bookingdates": {"checkin": "2026-13-45", "checkout": "2026-11-12"}},
        {**payload, "bookingdates": {"checkin": "2026-11-12", "checkout": "2026-11-10"}},
        {**payload, "firstname": "  "},
        {**payload, "depositpaid": "yes"},
        {**payload, "totalprice": "288"},
    ):
        requests.post(f"{base_url}/booking", json=bad_body, headers=bearer)

    booking_id = requests.post(f"{base_url}/booking", json=payload, headers=bearer).json()["bookingid"]
    requests.get(f"{base_url}/booking/{booking_id}")

    # 库存：未知房型（400）/ 卖到售罄（409）
    requests.post(f"{base_url}/booking?roomtype=nope", json=payload, headers=bearer)
    for _ in range(5):
        requests.post(f"{base_url}/booking?roomtype=limited", json=payload, headers=bearer)
    requests.post(f"{base_url}/booking?roomtype=limited", json=payload, headers=bearer)

    # 全量更新：路由不存在 / 没权限 / 查不到 / 校验失败 / 成功
    requests.put(f"{base_url}/no-such-route", json=payload, headers=bearer)
    requests.put(f"{base_url}/booking/{booking_id}", json=payload)
    requests.put(f"{base_url}/booking/999", json=payload, headers=bearer)
    requests.put(f"{base_url}/booking/{booking_id}", json={}, headers=bearer)
    requests.put(f"{base_url}/booking/{booking_id}", json=payload, headers=bearer)

    # 局部更新：同样四种分支
    requests.patch(f"{base_url}/no-such-route", json={}, headers=bearer)
    requests.patch(f"{base_url}/booking/{booking_id}", json={})
    requests.patch(f"{base_url}/booking/999", json={}, headers=bearer)
    requests.patch(f"{base_url}/booking/{booking_id}", json={"totalprice": "很贵"}, headers=bearer)
    requests.patch(f"{base_url}/booking/{booking_id}", json={"totalprice": 300}, headers=bearer)

    # 删除：路由不存在 / 没权限 / 查不到 / 成功 / 再删一次
    requests.delete(f"{base_url}/no-such-route", headers=bearer)
    requests.delete(f"{base_url}/booking/{booking_id}")
    requests.delete(f"{base_url}/booking/999", headers=bearer)
    requests.delete(f"{base_url}/booking/{booking_id}", headers=bearer)
    requests.delete(f"{base_url}/booking/{booking_id}", headers=bearer)

    # 剩下的分支：Cookie 鉴权、空请求体、未知路由的 POST
    requests.post(f"{base_url}/booking", json=payload, headers=cookie)
    requests.post(f"{base_url}/booking", headers=bearer)
    requests.post(f"{base_url}/no-such-route", json={})


def format_lines(numbers):
    """把 [1,2,3,7,9,10] 压成 "1-3、7、9-10"，方便看。"""
    groups = []
    start = previous = None
    for number in numbers:
        if start is None:
            start = previous = number
        elif number == previous + 1:
            previous = number
        else:
            groups.append((start, previous))
            start = previous = number
    if start is not None:
        groups.append((start, previous))
    return "、".join(str(a) if a == b else f"{a}-{b}" for a, b in groups)


def main():
    parser = argparse.ArgumentParser(description="零依赖语句覆盖率（被测文件：mock_server.py）")
    parser.add_argument("--min", type=float, default=0.0, help="覆盖率下限（百分数），低于就返回退出码 1")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(here, TARGET)
    if not os.path.exists(target_path):
        print(f"找不到被测文件：{target_path}")
        return 2

    executable = executable_lines(target_path)
    tracer = Tracer(target_path)
    tracer.start()
    try:
        import mock_server

        mock_server.STORE.reset()
        server, base_url = mock_server.start(port=0)
        try:
            scenario(base_url)
        finally:
            server.shutdown()
            server.server_close()
    finally:
        tracer.stop()

    hit = tracer.hit & executable
    ratio = 100.0 * len(hit) / len(executable)

    print(f"被测文件: {TARGET}")
    print(f"可执行行: {len(executable)}    已覆盖: {len(hit)}    覆盖率: {ratio:.1f}%")

    missing = sorted(executable - tracer.hit)
    if missing:
        print(f"未覆盖的行: {format_lines(missing)}")
        print("提示：未覆盖的多半是命令行入口 main() 和极端分支——入口行一般单独排除，不算漏测。")

    if args.min and ratio < args.min:
        print(f"覆盖率低于下限 {args.min:.1f}%，退出码 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
