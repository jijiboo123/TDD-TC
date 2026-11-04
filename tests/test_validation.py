"""参数校验与边界：缺字段、类型错、格式错、查不存在的资源。

正常路径谁都会测，异常路径才体现测试功力 —— 这类用例是面试最常问的。
"""

import pytest
import requests


def _post(base_url, headers, payload):
    return requests.post(f"{base_url}/booking", json=payload, headers=headers)


def test_missing_field_returns_400(base_url, auth_headers, booking_payload):
    payload = dict(booking_payload)
    payload.pop("firstname")
    assert _post(base_url, auth_headers, payload).status_code == 400


def test_missing_field_reports_which_one(base_url, auth_headers, booking_payload):
    payload = dict(booking_payload)
    payload.pop("lastname")
    assert "lastname" in _post(base_url, auth_headers, payload).json()["error"]


@pytest.mark.parametrize("bad_value", ["yes", 1, None])
def test_depositpaid_must_be_boolean(base_url, auth_headers, booking_payload, bad_value):
    payload = {**booking_payload, "depositpaid": bad_value}
    assert _post(base_url, auth_headers, payload).status_code == 400


@pytest.mark.parametrize("bad_price", ["288", None, [1]])
def test_totalprice_must_be_number(base_url, auth_headers, booking_payload, bad_price):
    payload = {**booking_payload, "totalprice": bad_price}
    assert _post(base_url, auth_headers, payload).status_code == 400


@pytest.mark.parametrize("bad_date", ["2026/11/10", "11-10-2026", "2026-11"])
def test_bookingdates_must_be_iso(base_url, auth_headers, booking_payload, bad_date):
    payload = {**booking_payload, "bookingdates": {"checkin": bad_date, "checkout": "2026-11-12"}}
    assert _post(base_url, auth_headers, payload).status_code == 400


def test_bookingdates_missing_keys_returns_400(base_url, auth_headers, booking_payload):
    payload = {**booking_payload, "bookingdates": {"checkin": "2026-11-10"}}
    assert _post(base_url, auth_headers, payload).status_code == 400


def test_get_unknown_booking_returns_404(base_url):
    assert requests.get(f"{base_url}/booking/999999").status_code == 404


def test_update_unknown_booking_returns_404(base_url, auth_headers, booking_payload):
    response = requests.put(f"{base_url}/booking/999999", json=booking_payload, headers=auth_headers)
    assert response.status_code == 404