"""UI 层夹具：起浏览器、每个用例一个干净页面。

为什么每个用例新建 context：context 之间 cookie / localStorage 完全隔离，
用例不会互相串登录态 —— 相当于接口测试里"每个用例前清空数据"。
"""

import pytest
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context()
    ui = context.new_page()
    ui.goto(f"{base_url}/")
    yield ui
    context.close()
