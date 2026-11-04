"""契约测试：响应结构不能悄悄变。"""

import requests

import contract


def test_booking_response_contract(base_url, auth_headers, booking_payload):
    response = requests.post(f"{base_url}/booking", json=booking_payload, headers=auth_headers)
    ok, detail = contract.compare("create_booking", response.json())
    assert ok, f"创建预订的响应结构变了 —— {detail}"


def test_error_response_contract(base_url, auth_headers):
    response = requests.post(f"{base_url}/booking", json={"firstname": "A"}, headers=auth_headers)
    ok, detail = contract.compare("error_response", response.json())
    assert ok, f"错误响应结构变了 —— {detail}"