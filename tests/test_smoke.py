"""冒烟测试：服务一挂就该立刻知道的那些检查。

和功能测试的区别：冒烟只关心"主干通不通"，不查细节。
CI 里通常先跑冒烟，挂了就不用跑后面几百个用例了。

运行：
    pytest -m smoke          # 只跑这一组
    pytest -m "not smoke"    # 跳过这一组
"""

import pytest
import requests

from assertions import assert_error_message, assert_fields_present, assert_json_field, assert_status

pytestmark = pytest.mark.smoke


def test_service_is_alive(base_url):
    assert_status(requests.get(f"{base_url}/ping"), 200, "健康检查")


def test_can_login(base_url):
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "password123"})
    assert_status(response, 200, "登录")
    assert_fields_present(response.json(), ["token"], "登录返回")


def test_can_create_booking(base_url, auth_headers, booking_payload):
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    assert_status(response, 200, "创建预订")
    assert_json_field(response.json(), "bookingid", response.json()["bookingid"], "自反检查")


def test_bad_login_explains_why(base_url):
    """失败信息要说清原因 —— 只说 401 的接口不好排查"""
    response = requests.post(f"{base_url}/auth", json={"username": "admin", "password": "x"})
    assert_status(response, 401, "错误密码")
    assert_error_message(response, "Bad credentials", "错误密码")