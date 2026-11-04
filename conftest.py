"""pytest 公共夹具：起服务、准备鉴权、造数据。

设计要点：
  - 服务在整个测试会话里只起一次（session 级），但每个用例前清空数据
  - 端口用 0 让系统分配，避免和别的进程抢端口
  - 造数据的夹具负责善后（yield 之后删除），用例之间不互相影响
"""

import os
import socket
import time

import pytest
import requests

import mock_server


def _wait_ready(base_url, timeout=5.0):
    """等 /ping 通，最多等 timeout 秒"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(f"{base_url}/ping", timeout=0.5).status_code == 200:
                return True
        except requests.RequestException:
            time.sleep(0.05)
    return False


@pytest.fixture(scope="session")
def base_url():
    # 设了 API_BASE_URL 就连真实服务，否则用本地 mock
    external = os.environ.get("API_BASE_URL")
    if external:
        assert _wait_ready(external), f"外部服务连不上: {external}"
        yield external
        return
    server, url = mock_server.start(port=0)
    assert _wait_ready(url), "mock 服务启动后 /ping 不通"
    yield url
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def clean_store():
    """每个用例开始前把数据清空 —— 否则用例顺序会影响结果"""
    mock_server.STORE.reset()
    yield


@pytest.fixture
def token(base_url):
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "password123"})
    assert response.status_code == 200
    return response.json()["token"]


@pytest.fixture
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def booking_payload():
    return {
        "firstname": "佳吉",
        "lastname": "刘",
        "totalprice": 288,
        "depositpaid": True,
        "bookingdates": {"checkin": "2026-11-10", "checkout": "2026-11-12"},
    }


@pytest.fixture
def created_booking(base_url, auth_headers, booking_payload):
    """造一条数据，用完删掉"""
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    yield {"id": body["bookingid"], "body": booking_payload}
    requests.delete(f"{base_url}/booking/{body['bookingid']}", headers=auth_headers)