"""库存：下单扣减、售罄拒绝、删除退还，以及并发下不能超卖。

超卖是电商/酒店系统最经典的并发缺陷：库存 5 间，10 个人同时下单，
"先查库存、再扣库存"两步之间没有锁，结果卖出 6、7 间。
这条用例就是专门去撞它的。
"""

import concurrent.futures

import allure
import requests

pytestmark = allure.feature("接口 · 库存")

LIMITED = "limited"


def book(base_url, headers, payload, index=0, roomtype=LIMITED):
    body = {**payload, "firstname": f"客{index}"}
    return requests.post(f"{base_url}/booking?roomtype={roomtype}", json=body, headers=headers, timeout=10)


def stock_of(base_url, roomtype=LIMITED):
    return requests.get(f"{base_url}/rooms").json()[roomtype]


def test_rooms_lists_stock(base_url):
    body = requests.get(f"{base_url}/rooms").json()
    assert body["limited"] == 5
    assert body["deluxe"] == 3


def test_booking_decrements_stock(base_url, auth_headers, booking_payload):
    before = stock_of(base_url)
    assert book(base_url, auth_headers, booking_payload).status_code == 200
    assert stock_of(base_url) == before - 1


def test_sold_out_returns_409(base_url, auth_headers, booking_payload):
    """只有 5 间，卖完第 6 单必须被拒。"""
    for index in range(5):
        assert book(base_url, auth_headers, booking_payload, index).status_code == 200
    response = book(base_url, auth_headers, booking_payload, 99)
    assert response.status_code == 409, response.text
    assert "售罄" in response.json()["error"]


def test_delete_releases_stock(base_url, auth_headers, booking_payload):
    """取消预订要把库存还回来，否则库存会越用越少。"""
    booking_id = book(base_url, auth_headers, booking_payload).json()["bookingid"]
    requests.delete(f"{base_url}/booking/{booking_id}", headers=auth_headers)
    assert stock_of(base_url) == 5


def test_concurrent_booking_does_not_oversell(base_url, auth_headers, booking_payload):
    """5 间房，10 个人同时抢：只能成功 5 单，库存归零，不能是负数。"""
    with allure.step("10 个线程同时抢 limited 房型"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            codes = list(pool.map(lambda i: book(base_url, auth_headers, booking_payload, i).status_code, range(10)))
        allure.attach(
            f"响应码：{sorted(codes)}\n成功：{codes.count(200)}  拒绝：{codes.count(409)}",
            name="并发结果", attachment_type=allure.attachment_type.TEXT)

    with allure.step("断言：正好 5 单成功、5 单被拒、库存归零"):
        assert codes.count(200) == 5, f"卖超了：{sorted(codes)}"
        assert codes.count(409) == 5, f"应该正好 5 单被拒：{sorted(codes)}"
        assert stock_of(base_url) == 0

    with allure.step("再确认库里真的只有 5 条"):
        listed = requests.get(f"{base_url}/booking?roomtype=limited").json()
        assert len(listed) == 5
