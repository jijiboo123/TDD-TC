"""增删改查主流程：一条数据从创建到删除的完整生命周期。"""

import allure
import requests

pytestmark = allure.feature("接口 · CRUD")


@allure.severity(allure.severity_level.CRITICAL)
@allure.story("创建预订")
def test_create_returns_booking_id(base_url, auth_headers, booking_payload):
    with allure.step("POST /booking 创建一条预订"):
        response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
        allure.attach(response.text, name="创建响应", attachment_type=allure.attachment_type.JSON)
    with allure.step("断言返回 200 且 bookingid 是整数"):
        assert response.status_code == 200
        assert isinstance(response.json().get("bookingid"), int)


def test_create_echoes_payload(base_url, auth_headers, booking_payload):
    body = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers).json()
    assert body["booking"] == booking_payload


def test_created_booking_is_readable(base_url, created_booking):
    response = requests.get(f"{base_url}/booking/{created_booking['id']}")
    assert response.status_code == 200
    assert response.json()["firstname"] == created_booking["body"]["firstname"]


def test_created_booking_appears_in_list(base_url, created_booking):
    ids = [item["bookingid"] for item in requests.get(f"{base_url}/booking").json()]
    assert created_booking["id"] in ids


def test_full_update_replaces_all_fields(base_url, auth_headers, created_booking, booking_payload):
    updated = {**booking_payload, "firstname": "小明", "totalprice": 999}
    response = requests.put(
        f"{base_url}/booking/{created_booking['id']}", json=updated, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["firstname"] == "小明"
    assert response.json()["totalprice"] == 999


def test_partial_update_changes_only_given_field(base_url, auth_headers, created_booking):
    original_lastname = created_booking["body"]["lastname"]
    response = requests.patch(
        f"{base_url}/booking/{created_booking['id']}", json={"totalprice": 66}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["totalprice"] == 66
    assert response.json()["lastname"] == original_lastname


def test_delete_returns_201(base_url, auth_headers, created_booking):
    response = requests.delete(f"{base_url}/booking/{created_booking['id']}", headers=auth_headers)
    assert response.status_code == 201


def test_deleted_booking_is_gone(base_url, auth_headers, created_booking):
    key = created_booking["id"]
    requests.delete(f"{base_url}/booking/{key}", headers=auth_headers)
    assert requests.get(f"{base_url}/booking/{key}").status_code == 404


def test_delete_twice_returns_404(base_url, auth_headers, created_booking):
    key = created_booking["id"]
    requests.delete(f"{base_url}/booking/{key}", headers=auth_headers)
    assert requests.delete(f"{base_url}/booking/{key}", headers=auth_headers).status_code == 404