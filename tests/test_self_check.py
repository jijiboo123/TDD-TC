"""自检程序本身的测试：防止它自己坏了却"报绿"。

自检工具最危险的情况是：它自己算错了，却告诉你项目一切正常。
所以这里验证它的两个核心能力：必需文件清单、文档数字提取。
"""

import allure
import pytest

import self_check

pytestmark = allure.feature("项目自检")


def test_required_files_all_exist():
    missing = [name for name in self_check.REQUIRED if not (self_check.ROOT / name).exists()]
    assert missing == [], f"项目结构缺文件：{missing}"


def test_doc_numbers_are_parsed():
    numbers = self_check.doc_numbers()
    assert isinstance(numbers.get("readme_api"), int)
    assert isinstance(numbers.get("readme_total"), int)
    assert numbers["readme_total"] > numbers["readme_api"]


def test_parse_junit_counts(tmp_path):
    xml = tmp_path / "report.xml"
    xml.write_text(
        '<?xml version="1.0"?><testsuites><testsuite name="pytest" '
        'tests="5" failures="1" errors="0" skipped="2"/></testsuites>',
        encoding="utf-8",
    )
    stats = self_check.parse_junit(xml)
    assert stats == {"tests": 5, "failures": 1, "errors": 0, "skipped": 2}
