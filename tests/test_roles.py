"""角色权限：admin 能写，viewer 只能读。

越权是接口测试最容易漏的一类问题——功能用例全绿，但一个只读账号能把数据删了。
这类用例的价值往往比 10 条 CRUD 还高。
"""

import allure
import requests

pytestmark = allure.feature("接口 · 角色权限")


def test_admin_can_create(base_url, auth_headers, booking_payload):
    """admin 有写权限：正常创建。"""
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    assert response.status_code == 200, response.text


def test_viewer_can_read(base_url, viewer_headers, created_booking):
    """viewer 至少能查——不能连读都挡住。"""
    assert requests.get(f"{base_url}/booking", headers=viewer_headers).status_code == 200
    response = requests.get(f"{base_url}/booking/{created_booking['id']}", headers=viewer_headers)
    assert response.status_code == 200


def test_viewer_cannot_create(base_url, viewer_headers, booking_payload):
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=viewer_headers)
    assert response.status_code == 403, response.text
    assert "admin" in response.json()["error"]


def test_viewer_cannot_update(base_url, viewer_headers, created_booking, booking_payload):
    """全量更新也是写操作，viewer 必须被拒。"""
    updated = {**booking_payload, "totalprice": 1}
    response = requests.put(
        f"{base_url}/booking/{created_booking['id']}", json=updated, headers=viewer_headers)
    assert response.status_code == 403, response.text


def test_viewer_cannot_patch(base_url, viewer_headers, created_booking):
    """局部更新同样要拦。"""
    response = requests.patch(
        f"{base_url}/booking/{created_booking['id']}", json={"totalprice": 1}, headers=viewer_headers)
    assert response.status_code == 403, response.text


def test_viewer_cannot_delete(base_url, viewer_headers, created_booking):
    """最危险的一条：viewer 删除必须被拒，而且数据要还在。"""
    key = created_booking["id"]
    response = requests.delete(f"{base_url}/booking/{key}", headers=viewer_headers)
    assert response.status_code == 403, response.text
    assert requests.get(f"{base_url}/booking/{key}").status_code == 200
