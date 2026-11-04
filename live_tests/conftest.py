"""真实公开 API（dummyjson.com）的联网用例夹具。

和本地 mock 套件的区别：
  - 默认不跑：只有设了 LIVE_API=1 才执行，日常回归不会被外网拖慢；
  - 不共享本地夹具：真实服务的 URL、账号、数据结构都不一样；
  - 网络不通时整组 skip，而不是红一片——这不是被测系统的错。
"""

import os

import pytest
import requests

DEFAULT_URL = "https://dummyjson.com"


def pytest_collection_modifyitems(config, items):
    if os.environ.get("LIVE_API") == "1":
        return
    skip = pytest.mark.skip(reason="联网用例：设 LIVE_API=1 才执行（或双击 运行真实API测试.bat）")
    for item in items:
        item.add_marker(skip)


@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("LIVE_API_URL", DEFAULT_URL).rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def reachable(base_url):
    """连不上就直接整组 skip：网络问题不该报成"测试失败"。"""
    try:
        response = requests.get(f"{base_url}/posts?limit=1", timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        pytest.skip(f"真实 API 不可达（{base_url}）：{error}")
    return True


@pytest.fixture(scope="session")
def token(base_url):
    response = requests.post(
        f"{base_url}/auth/login",
        json={"username": "emilys", "password": "emilyspass"},
        timeout=15,
    )
    assert response.status_code == 200, response.text
    return response.json()["accessToken"]


@pytest.fixture(scope="session")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
