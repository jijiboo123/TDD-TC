"""健康检查与路由：服务活着、返回格式对、不存在的地址要 404。"""

import requests


def test_ping_returns_200(base_url):
    response = requests.get(f"{base_url}/ping")
    assert response.status_code == 200


def test_ping_returns_pong(base_url):
    assert requests.get(f"{base_url}/ping").json() == "pong"


def test_unknown_route_returns_404(base_url):
    assert requests.get(f"{base_url}/nope").status_code == 404


def test_booking_list_is_json_array(base_url):
    response = requests.get(f"{base_url}/booking")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_response_has_json_content_type(base_url):
    response = requests.get(f"{base_url}/booking")
    assert "application/json" in response.headers.get("Content-Type", "")