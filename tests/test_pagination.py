"""分页与过滤：列表接口最容易出边界问题的地方。

思路：先造 5 条数据，再看第 1 页 / 第 2 页 / 最后一页 / 越界页分别返回什么。
分页的 bug 往往不在"正常页"，而在"最后一页"和"越界页"。
"""

import allure
import pytest
import requests

pytestmark = allure.feature("接口 · 分页与过滤")


def make_bookings(base_url, headers, payload, count, roomtype="standard"):
    """造 count 条数据，返回 id 列表（按创建顺序）。"""
    ids = []
    for index in range(count):
        body = {**payload, "firstname": f"客{index}"}
        response = requests.post(f"{base_url}/booking?roomtype={roomtype}", json=body, headers=headers)
        assert response.status_code == 200, response.text
        ids.append(response.json()["bookingid"])
    return ids


def test_first_page_returns_requested_size(base_url, auth_headers, booking_payload):
    make_bookings(base_url, auth_headers, booking_payload, 5)
    body = requests.get(f"{base_url}/booking?page=1&size=2").json()
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["total"] == 5
    assert len(body["items"]) == 2


def test_second_page_continues(base_url, auth_headers, booking_payload):
    ids = make_bookings(base_url, auth_headers, booking_payload, 5)
    body = requests.get(f"{base_url}/booking?page=2&size=2").json()
    assert [item["bookingid"] for item in body["items"]] == ids[2:4]


def test_last_page_can_be_partial(base_url, auth_headers, booking_payload):
    """5 条按每页 2 条分，第 3 页只剩 1 条——这是最容易写成"满页"的地方。"""
    make_bookings(base_url, auth_headers, booking_payload, 5)
    body = requests.get(f"{base_url}/booking?page=3&size=2").json()
    assert len(body["items"]) == 1
    assert body["total"] == 5


def test_page_beyond_end_is_empty_not_error(base_url, auth_headers, booking_payload):
    """越界页应该返回空列表而不是 500 或报错。"""
    make_bookings(base_url, auth_headers, booking_payload, 3)
    response = requests.get(f"{base_url}/booking?page=9&size=2")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 3


@pytest.mark.parametrize("size", [0, -1, 101])
def test_illegal_size_is_rejected(base_url, auth_headers, booking_payload, size):
    make_bookings(base_url, auth_headers, booking_payload, 1)
    response = requests.get(f"{base_url}/booking?page=1&size={size}")
    assert response.status_code == 400, response.text


def test_filter_by_roomtype(base_url, auth_headers, booking_payload):
    """按房型过滤：只返回这个房型的单子，total 也要跟着变。"""
    make_bookings(base_url, auth_headers, booking_payload, 2, roomtype="limited")
    make_bookings(base_url, auth_headers, booking_payload, 3, roomtype="standard")

    body = requests.get(f"{base_url}/booking?roomtype=limited").json()
    assert len(body) == 2

    paged = requests.get(f"{base_url}/booking?page=1&size=10&roomtype=limited").json()
    assert paged["total"] == 2
