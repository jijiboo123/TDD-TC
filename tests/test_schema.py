"""契约校验（JSON Schema）：光有类型不够，值的规则也要写死。

和 `test_contract.py` 的分工：
  - `contract.py` 快照：记录"结构长什么样"，结构变了就红；
  - 这里的 schema：手写规则"什么值才算合法"（必填、范围、枚举、真实日期），
    契约写错、服务端返回脏数据，都会红。

跑：
    python -m pytest tests/test_schema.py -v
"""

from pathlib import Path

import allure
import pytest
import requests

from schema_validator import SchemaError, load, validate

pytestmark = allure.feature("契约 · JSON Schema")

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


def schema(name):
    return load(SCHEMA_DIR / name)


@allure.severity(allure.severity_level.CRITICAL)
@allure.story("创建响应契约")
def test_created_booking_matches_schema(base_url, auth_headers, booking_payload):
    """创建响应：id 是正整数，booking 里 5 个字段齐全、类型对、值合法。"""
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    assert response.status_code == 200
    with allure.step("按 booking_created.schema.json 校验响应"):
        validate(response.json(), schema("booking_created.schema.json"), "创建响应")


def test_booking_detail_matches_schema(base_url, created_booking):
    """详情响应也守同一份 booking 契约（复用 $ref，不重复写规则）。"""
    response = requests.get(f"{base_url}/booking/{created_booking['id']}")
    validate(response.json(), schema("booking.schema.json"), "预订详情")


def test_booking_list_matches_schema(base_url, created_booking):
    """列表：数组，每项只有 bookingid，不能多出别的字段。"""
    response = requests.get(f"{base_url}/booking")
    validate(response.json(), schema("booking_list.schema.json"), "预订列表")


def test_error_response_matches_schema(base_url, auth_headers):
    """错误响应：必须有非空 error 字段，前端才能展示原因。"""
    response = requests.post(f"{base_url}/booking", json={}, headers=auth_headers)
    assert response.status_code == 400
    validate(response.json(), schema("error.schema.json"), "错误响应")


def test_paged_list_matches_schema(base_url, auth_headers, booking_payload):
    """分页响应的信封结构：items/total/page/size 一个都不能少。"""
    requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    body = requests.get(f"{base_url}/booking?page=1&size=1").json()
    validate(body, schema("booking_page.schema.json"), "分页响应")


# ---- 下面三条测的是"校验器自己"：schema 写错、数据变脏时测试要能发现 ----


def test_validator_rejects_wrong_type():
    with pytest.raises(SchemaError) as error:
        validate({"bookingid": "1", "booking": {}}, schema("booking_created.schema.json"))
    assert "integer" in str(error.value)


def test_validator_rejects_negative_price(booking_payload):
    dirty = {"bookingid": 1, "booking": {**booking_payload, "totalprice": -1}}
    with pytest.raises(SchemaError) as error:
        validate(dirty, schema("booking_created.schema.json"))
    assert "不能小于 0" in str(error.value)


def test_validator_rejects_fake_date(booking_payload):
    dates = {"checkin": "2026-13-45", "checkout": "2026-11-12"}
    dirty = {"bookingid": 1, "booking": {**booking_payload, "bookingdates": dates}}
    with pytest.raises(SchemaError) as error:
        validate(dirty, schema("booking_created.schema.json"))
    assert "真实存在的日期" in str(error.value)
