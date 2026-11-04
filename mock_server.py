"""本地 mock 的「预订管理」API —— 模仿 restful-booker 的接口形状。

为什么要本地 mock：restful-booker 部署在 Heroku 免费实例上，2026 年已经下线
（实测 HTTP 000）。测试练习不该被别人的服务器卡住，所以这里用标准库实现一份
同样形状的接口，行为（含错误码和鉴权）按真实语义来。

启动：
    python mock_server.py            # 默认 127.0.0.1:8321
    python mock_server.py --port 9000
"""

import argparse
import json
from datetime import datetime
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BOOKING_FIELDS = ("firstname", "lastname", "totalprice", "depositpaid", "bookingdates")


class Store:
    """内存存储。每个测试会话开始时清空，避免用例互相污染。"""

    def __init__(self):
        self.next_id = 1
        self.items = {}
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.next_id = 1
            self.items.clear()

    def create(self, body):
        with self.lock:
            key = self.next_id
            self.next_id += 1
            self.items[key] = body
            return key

    def all(self):
        with self.lock:
            return dict(self.items)

    def delete(self, key):
        """查和删必须在同一把锁里 —— 否则两个并发删除会都返回 201（都以为自己删成功了）。"""
        with self.lock:
            return self.items.pop(key, None) is not None


STORE = Store()
VALID_TOKEN = "test-token-123"


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

    def _authorized(self):
        """两种写法都认：Authorization: Bearer xxx 或 Cookie: token=xxx"""
        auth = self.headers.get("Authorization") or ""
        if auth.startswith("Bearer ") and auth[7:] == VALID_TOKEN:
            return True
        cookie = self.headers.get("Cookie") or ""
        return f"token={VALID_TOKEN}" in cookie

    # ---- 路由 ----
    def do_GET(self):
        if self.path == "/ping":
            return self._send(200, "pong")
        if self.path == "/booking":
            return self._send(200, [{"bookingid": k} for k in STORE.all()])
        match = re.fullmatch(r"/booking/(\d+)", self.path)
        if match:
            item = STORE.all().get(int(match.group(1)))
            return self._send(200, item) if item else self._send(404, {"error": "not found"})
        return self._send(404, {"error": "no such route"})

    def do_POST(self):
        if self.path == "/auth":
            body = self._read_json() or {}
            if body.get("username") == "admin" and body.get("password") == "password123":
                return self._send(200, {"token": VALID_TOKEN})
            return self._send(401, {"reason": "Bad credentials"})
        if self.path == "/booking":
            if not self._authorized():
                return self._send(403, {"error": "forbidden"})
            body = self._read_json()
            error = validate(body)
            if error:
                return self._send(400, {"error": error})
            key = STORE.create(body)
            return self._send(200, {"bookingid": key, "booking": body})
        return self._send(404, {"error": "no such route"})

    def do_PUT(self):
        match = re.fullmatch(r"/booking/(\d+)", self.path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if not self._authorized():
            return self._send(403, {"error": "forbidden"})
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
        match = re.fullmatch(r"/booking/(\d+)", self.path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if not self._authorized():
            return self._send(403, {"error": "forbidden"})
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
        match = re.fullmatch(r"/booking/(\d+)", self.path)
        if not match:
            return self._send(404, {"error": "no such route"})
        if not self._authorized():
            return self._send(403, {"error": "forbidden"})
        key = int(match.group(1))
        if not STORE.delete(key):
            return self._send(404, {"error": "not found"})
        return self._send(201, "Created")

def start(port=0):
    """在后台线程起服务，返回 (server, base_url)。port=0 让系统分配空闲端口。"""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def main():
    parser = argparse.ArgumentParser(description="本地 mock 预订 API")
    parser.add_argument("--port", type=int, default=8321)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"mock 服务已启动: http://127.0.0.1:{args.port}")
    print("  例: curl http://127.0.0.1:8321/ping")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()