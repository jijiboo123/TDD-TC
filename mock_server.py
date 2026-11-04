"""本地 mock 的「预订管理」API —— 模仿 restful-booker 的接口形状，再补上真实业务该有的东西。

为什么是本地 mock：restful-booker 部署在 Heroku 免费实例上，2026 年已经下线
（实测 HTTP 000）。测试练习不该被别人的服务器卡住，所以这里用标准库实现一份
同样形状的接口，行为（含错误码和鉴权）按真实语义来。

除了基础 CRUD，还实现了三样真实系统才有的东西（这样测试才有东西可测）：
  - 角色权限：admin 可写，viewer 只读（/auth 用不同账号登录拿不同 token）
  - 分页与过滤：GET /booking?page=1&size=10&roomtype=limited
  - 房间库存：POST /booking?roomtype=limited 会扣库存，售罄返回 409

启动：
    python mock_server.py            # 默认 127.0.0.1:8321
    python mock_server.py --port 9000
"""

import argparse
import json
from datetime import datetime
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BOOKING_FIELDS = ("firstname", "lastname", "totalprice", "depositpaid", "bookingdates")

# 房型 → 初始库存。standard 故意给大一点，老的并发用例（建 30 条）不会被库存挡住。
ROOM_STOCK = {"standard": 1000, "limited": 5, "deluxe": 3}

# 账号 → 密码 / 角色 / token。真实系统会查库，这里是内存表。
USERS = {
    "admin": {"password": "password123", "role": "admin", "token": "test-token-123"},
    "viewer": {"password": "viewer123", "role": "viewer", "token": "viewer-token-456"},
}
TOKENS = {user["token"]: user["role"] for user in USERS.values()}


class Store:
    """内存存储。每个测试会话开始时清空，避免用例互相污染。"""

    def __init__(self):
        self.next_id = 1
        self.items = {}
        self.meta = {}      # bookingid -> {"roomtype": ...}，不混进 booking 响应体
        self.stock = dict(ROOM_STOCK)
        self.idempotent = {}    # Idempotency-Key -> bookingid，重复提交要返回同一单
        self.lock = threading.RLock()   # 可重入：create_once 里要复用同一把锁

    def reset(self):
        with self.lock:
            self.next_id = 1
            self.items.clear()
            self.meta.clear()
            self.stock = dict(ROOM_STOCK)
            self.idempotent.clear()

    def all(self):
        with self.lock:
            return dict(self.items)

    def get(self, key):
        with self.lock:
            return self.items.get(key)

    def create_once(self, body, roomtype, idempotency_key=None):
        """幂等创建：查重、扣库存、发号、记账，全部在同一把锁里完成。

        返回 (bookingid, 是否新建)：
          - 同一个 key 第二次来 → 返回原来的 id，created=False，不重复扣库存；
          - 库存不足 → (None, False)。
        """
        with self.lock:
            if idempotency_key and idempotency_key in self.idempotent:
                return self.idempotent[idempotency_key], False
            if self.stock.get(roomtype, 0) <= 0:
                return None, False
            self.stock[roomtype] -= 1
            key = self.next_id
            self.next_id += 1
            self.items[key] = body
            self.meta[key] = {"roomtype": roomtype}
            if idempotency_key:
                self.idempotent[idempotency_key] = key
            return key, True

    def delete(self, key):
        """查和删必须在同一把锁里 —— 否则两个并发删除会都返回 201。删成功要退还库存。"""
        with self.lock:
            body = self.items.pop(key, None)
            meta = self.meta.pop(key, None)
            if body is None:
                return False
            # 单子删了，指向它的幂等键也一起失效，避免重放时返回"幽灵单"
            for token in [name for name, booking_id in self.idempotent.items() if booking_id == key]:
                self.idempotent.pop(token, None)
            if meta:
                room = meta.get("roomtype", "standard")
                self.stock[room] = self.stock.get(room, 0) + 1
            return True

    # ---- 库存 ----
    def stock_snapshot(self):
        with self.lock:
            return dict(self.stock)


STORE = Store()


def validate(body):
    """返回错误说明或 None。真实 API 缺字段会 500，这里用 400 更合理，测试里都覆盖。"""
    if not isinstance(body, dict):
        return "body 必须是 JSON 对象"
    for field in BOOKING_FIELDS:
        if field not in body:
            return f"缺少字段 {field}"
    dates = body.get("bookingdates") or {}
    if not isinstance(dates, dict) or "checkin" not in dates or "checkout" not in dates:
        return "bookingdates 需要 checkin 与 checkout"
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for key in ("checkin", "checkout"):
        if not pattern.match(str(dates.get(key, ""))):
            return f"bookingdates.{key} 要写成 YYYY-MM-DD"
    # 空名字没有意义，应当拒绝（这条是数据驱动用例发现的）
    for field in ("firstname", "lastname"):
        if not str(body.get(field, "")).strip():
            return f"{field} 不能为空"
    # 正则只管位数，管不了 2026-13-45 这种假日期（也是测试发现的）
    try:
        checkin = datetime.strptime(str(dates["checkin"]), "%Y-%m-%d")
        checkout = datetime.strptime(str(dates["checkout"]), "%Y-%m-%d")
    except ValueError:
        return "bookingdates 里的日期不是合法日期"
    if checkout <= checkin:
        return "退房日期必须晚于入住日期"
    if not isinstance(body.get("depositpaid"), bool):
        return "depositpaid 必须是布尔值"
    if not isinstance(body.get("totalprice"), (int, float)):
        return "totalprice 必须是数字"
    # 负数价格没有业务含义（等价类里"无效类：负数"漏测，被补的用例抓到）
    if body["totalprice"] < 0:
        return "totalprice 不能是负数"
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass      # 别刷屏

    # ---- 工具 ----
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _send_page(self):
        """把 web/index.html 发给浏览器 —— UI 层用例就是点这个页面。"""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")
        try:
            with open(path, "rb") as handle:
                body = handle.read()
        except OSError:
            return self._send(404, {"error": "页面文件缺失：web/index.html"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self):
        """把 /booking?page=2&size=5 拆成 路径 + 参数字典。"""
        parsed = urlparse(self.path)
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        return parsed.path, query

    def _role(self):
        """两种写法都认：Authorization: Bearer xxx 或 Cookie: token=xxx。查不到返回 None。"""
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            return TOKENS.get(auth[7:])
        cookie = self.headers.get("Cookie") or ""
        matched = re.search(r"token=([^;]+)", cookie)
        return TOKENS.get(matched.group(1)) if matched else None

    def _admin_only(self):
        """权限不够时已经发了 403，返回 True；有权限返回 False。"""
        role = self._role()
        if role is None:
            self._send(403, {"error": "forbidden"})
            return True
        if role != "admin":
            self._send(403, {"error": "需要 admin 权限"})
            return True
        return False

    # ---- 路由 ----
    def do_GET(self):
        path, query = self._route()
        if path == "/":
            return self._send_page()
        if path == "/ping":
            return self._send(200, "pong")
        if path == "/rooms":
            return self._send(200, STORE.stock_snapshot())
        if path == "/booking":
            return self._list_bookings(query)
        match = re.fullmatch(r"/booking/(\d+)", path)
        if match:
            item = STORE.all().get(int(match.group(1)))
            return self._send(200, item) if item else self._send(404, {"error": "not found"})
        return self._send(404, {"error": "no such route"})

    def _list_bookings(self, query):
        """不带 page/size 时保持老行为（返回数组）；带了就返回分页信封。"""
        rows = [(key, STORE.meta.get(key, {}).get("roomtype", "standard")) for key in STORE.all()]
        if "roomtype" in query:
            rows = [row for row in rows if row[1] == query["roomtype"]]

        if "page" not in query and "size" not in query:
            return self._send(200, [{"bookingid": key} for key, _ in rows])

        try:
            page = int(query.get("page", "1"))
            size = int(query.get("size", "10"))
        except ValueError:
            return self._send(400, {"error": "page 和 size 必须是整数"})
        if page < 1:
            return self._send(400, {"error": "page 从 1 开始"})
        if not 1 <= size <= 100:
            return self._send(400, {"error": "size 必须在 1 到 100 之间"})

        start = (page - 1) * size
        chunk = rows[start:start + size]
        return self._send(200, {
            "items": [{"bookingid": key} for key, _ in chunk],
            "total": len(rows),
            "page": page,
            "size": size,
        })

    def do_POST(self):
        path, query = self._route()
        if path == "/auth":
            body = self._read_json() or {}
            user = USERS.get(str(body.get("username")))
            if user and user["password"] == body.get("password"):
                return self._send(200, {"token": user["token"], "role": user["role"]})
            return self._send(401, {"reason": "Bad credentials"})
        if path == "/booking":
            if self._admin_only():
                return
            body = self._read_json()
            error = validate(body)
            if error:
                return self._send(400, {"error": error})
            roomtype = query.get("roomtype", "standard")
            if roomtype not in ROOM_STOCK:
                return self._send(400, {"error": f"未知房型 {roomtype}"})
            idem_key = self.headers.get("Idempotency-Key")
            key, created = STORE.create_once(body, roomtype, idem_key)
            if key is None:
                return self._send(409, {"error": f"{roomtype} 房间已售罄"})
            # 重复提交返回的是"原来那一单"，不会多建一条、也不会重复扣库存
            return self._send(200, {"bookingid": key, "booking": body if created else STORE.get(key)})
        return self._send(404, {"error": "no such route"})

    def do_PUT(self):
        path, _ = self._route()
        match = re.fullmatch(r"/booking/(\d+)", path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if self._admin_only():
            return
        key = int(match.group(1))
        with STORE.lock:
            exists = key in STORE.items
        if not exists:
            return self._send(404, {"error": "not found"})
        body = self._read_json()
        error = validate(body)
        if error:
            return self._send(400, {"error": error})
        with STORE.lock:
            STORE.items[key] = body
        return self._send(200, body)

    def do_PATCH(self):
        path, _ = self._route()
        match = re.fullmatch(r"/booking/(\d+)", path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if self._admin_only():
            return
        key = int(match.group(1))
        with STORE.lock:
            current = STORE.items.get(key)
        if current is None:
            return self._send(404, {"error": "not found"})
        patch = self._read_json() or {}
        merged = {**current, **patch}
        error = validate(merged)
        if error:
            return self._send(400, {"error": error})
        with STORE.lock:
            STORE.items[key] = merged
        return self._send(200, merged)

    def do_DELETE(self):
        path, _ = self._route()
        match = re.fullmatch(r"/booking/(\d+)", path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if self._admin_only():
            return
        key = int(match.group(1))
        if not STORE.delete(key):
            return self._send(404, {"error": "not found"})
        return self._send(201, "Created")


class Server(ThreadingHTTPServer):
    """监听队列放大到 64：默认只有 5，压测时连接会在队列里排队，p99 被拖到几百毫秒。"""

    request_queue_size = 64
    daemon_threads = True


def start(port=0):
    """在后台线程起服务，返回 (server, base_url)。port=0 让系统分配空闲端口。"""
    server = Server(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def main():
    parser = argparse.ArgumentParser(description="本地 mock 预订 API")
    parser.add_argument("--port", type=int, default=8321)
    args = parser.parse_args()
    server = Server(("127.0.0.1", args.port), Handler)
    print(f"mock 服务已启动: http://127.0.0.1:{args.port}")
    print("  例: curl http://127.0.0.1:8321/ping")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
