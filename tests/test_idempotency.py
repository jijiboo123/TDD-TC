"""幂等：同一个 Idempotency-Key 重复提交，只应该成功一次。

为什么需要它：用户手抖点两下"提交"、客户端超时重试、消息队列重投，
都会让同一个请求到达两次。没有幂等键，就会重复下单、重复扣库存、重复扣款。

接口约定：请求头带 `Idempotency-Key: <业务唯一号>`，
重复提交返回**第一次那一单**（同一个 bookingid），不会多建、也不会重复扣库存。
"""

import concurrent.futures

import allure
import requests

pytestmark = allure.feature("接口 · 幂等")


def book(base_url, headers, payload, key=None, index=0, roomtype="standard"):
    body = {**payload, "firstname": f"客{index}"}
    extra = {"Idempotency-Key": key} if key else {}
    return requests.post(
        f"{base_url}/booking?roomtype={roomtype}",
        json=body,
        headers={**headers, **extra},
        timeout=10,
    )


def test_same_key_returns_the_same_booking(base_url, auth_headers, booking_payload):
    """同一个 key 提交两次：返回同一个 bookingid，库里只有一条。"""
    first = book(base_url, auth_headers, booking_payload, key="order-001")
    second = book(base_url, auth_headers, booking_payload, key="order-001")

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["bookingid"] == second.json()["bookingid"]
    assert len(requests.get(f"{base_url}/booking").json()) == 1


def test_same_key_consumes_stock_once(base_url, auth_headers, booking_payload):
    """重复提交不能重复扣库存。"""
    before = requests.get(f"{base_url}/rooms").json()["standard"]
    book(base_url, auth_headers, booking_payload, key="order-002")
    book(base_url, auth_headers, booking_payload, key="order-002")
    after = requests.get(f"{base_url}/rooms").json()["standard"]
    assert before - after == 1


def test_different_keys_create_different_bookings(base_url, auth_headers, booking_payload):
    a = book(base_url, auth_headers, booking_payload, key="order-a")
    b = book(base_url, auth_headers, booking_payload, key="order-b")
    assert a.json()["bookingid"] != b.json()["bookingid"]
    assert len(requests.get(f"{base_url}/booking").json()) == 2


def test_without_key_duplicates_are_allowed(base_url, auth_headers, booking_payload):
    """不带 key 时保持老行为：两次提交就是两单。"""
    book(base_url, auth_headers, booking_payload)
    book(base_url, auth_headers, booking_payload)
    assert len(requests.get(f"{base_url}/booking").json()) == 2


def test_concurrent_same_key_creates_only_one_booking(base_url, auth_headers, booking_payload):
    """10 个线程拿同一个 key 同时提交：只能建出一单。

    这是幂等最容易出错的地方——"先查 key、再建单"如果不在同一把锁里，
    并发时会同时查不到，然后各建一单。
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(
            pool.map(lambda i: book(base_url, auth_headers, booking_payload, key="order-race", index=i), range(10))
        )

    codes = [response.status_code for response in responses]
    assert codes.count(200) == 10, f"并发幂等请求应该都成功：{sorted(codes)}"
    ids = {response.json()["bookingid"] for response in responses}
    assert len(ids) == 1, f"同一个幂等键建出了多单：{sorted(ids)}"
    assert len(requests.get(f"{base_url}/booking").json()) == 1
