"""参数校验与边界：缺字段、类型错、格式错、查不存在的资源。

正常路径谁都会测，异常路径才体现测试功力 —— 这类用例是面试最常问的。
"""

import allure
import pytest
import requests

pytestmark = allure.feature("接口 · 参数校验")


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


# ---- 下面这几条是"等价类 + 边界值"补出来的，也是缺陷 4 的来源 ----

@allure.severity(allure.severity_level.NORMAL)
@allure.story("金额范围（BUG-004 回归）")
def test_negative_price_is_rejected(base_url, auth_headers, booking_payload):
    """价格是负数没有业务含义 —— 等价类里的"无效类：负数"必须有对应用例。"""
    payload = {**booking_payload, "totalprice": -1}
    with allure.step("提交 totalprice=-1 的预订"):
        response = _post(base_url, auth_headers, payload)
        allure.attach(response.text, name="服务端拒绝原因", attachment_type=allure.attachment_type.JSON)
    with allure.step("断言被拒绝（400）"):
        assert response.status_code == 400, f"负数价格竟然创建成功了：{response.text}"


def test_same_day_checkin_and_checkout_is_rejected(base_url, auth_headers, booking_payload):
    """边界值：入住日 == 退房日 = 住 0 晚，业务上不该成立。"""
    payload = {**booking_payload, "bookingdates": {"checkin": "2026-11-10", "checkout": "2026-11-10"}}
    assert _post(base_url, auth_headers, payload).status_code == 400


@pytest.mark.parametrize(
    ("checkin", "checkout", "expect"),
    [
        ("2028-02-29", "2028-03-01", 200),   # 闰年：2 月 29 日存在
        ("2026-02-29", "2026-03-01", 400),   # 平年：2 月 29 日不存在
    ],
)
def test_leap_day_boundary(base_url, auth_headers, booking_payload, checkin, checkout, expect):
    """边界值：日期的"存在性"靠 strptime 判断，闰年是最容易漏的边界。"""
    payload = {**booking_payload, "bookingdates": {"checkin": checkin, "checkout": checkout}}
    assert _post(base_url, auth_headers, payload).status_code == expect