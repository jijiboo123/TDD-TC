"""数据驱动：用例数据在 data/booking_cases.json 里，这里只写逻辑。

好处：加一个测试场景 = 在 JSON 里加一行，不用碰代码。
这也是"测试数据与测试逻辑分离"的基本功。
"""

import json
from pathlib import Path

import allure
import pytest
import requests

from assertions import assert_status

pytestmark = allure.feature("数据驱动")

CASES_FILE = Path(__file__).resolve().parent.parent / "data" / "booking_cases.json"
CASES = json.loads(CASES_FILE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_booking_cases(base_url, auth_headers, case):
    response = requests.post(f"{base_url}/booking", json=case["payload"], headers=auth_headers)
    assert_status(response, case["expect"], case["id"])