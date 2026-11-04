"""UI 层用例：站在用户视角点页面，验证「接口 + 前端 + 渲染」整条链路。

和接口用例的区别：
  - 接口用例断言 JSON，UI 用例断言"页面上看得见的东西"；
  - 页面把多个接口串起来（登录 → 创建 → 刷新列表），一个 UI 用例能覆盖整条链路；
  - 断言用 Playwright 的 expect()，它会自动等待元素出现，不用手写 sleep。

先装环境（只需一次）：
    pip install -r requirements-ui.txt
    python -m playwright install chromium

跑：
    python -m pytest ui_tests -v
"""

import allure
import pytest
from playwright.sync_api import expect

pytestmark = [pytest.mark.ui, allure.feature("UI · 预订管理")]


def login(page):
    page.click("#login")
    expect(page.locator("#login-state")).to_have_text("已登录")


def create_booking(page, firstname="佳吉", lastname="刘", totalprice="288"):
    page.fill("#firstname", firstname)
    page.fill("#lastname", lastname)
    page.fill("#totalprice", totalprice)
    page.click("#create")


def test_page_opens_with_empty_list(page):
    """打开页面：标题对、列表空、没登录时创建按钮是禁用的。"""
    assert page.title() == "预订管理"
    expect(page.locator("#page-title")).to_have_text("预订管理")
    expect(page.locator("#booking-rows tr")).to_have_count(0)
    expect(page.locator("#create")).to_be_disabled()


def test_login_unlocks_create(page):
    """登录成功后：状态变"已登录"、创建按钮解锁。"""
    expect(page.locator("#login-state")).to_have_text("未登录")
    login(page)
    expect(page.locator("#message")).to_have_text("登录成功")
    expect(page.locator("#create")).to_be_enabled()


def test_create_booking_appears_in_list(page):
    """创建后列表出现这一行，姓名和价格都对 —— 前端渲染 + 接口回写一起验。"""
    login(page)
    create_booking(page)
    expect(page.locator("#booking-rows tr")).to_have_count(1)
    row = page.locator("#booking-rows tr").first
    expect(row).to_contain_text("佳吉 刘")
    expect(row).to_contain_text("288")


def test_empty_firstname_shows_backend_error(page):
    """名字留空：后端 400，页面把原因展示出来，列表不新增。"""
    login(page)
    create_booking(page, firstname=" ")
    expect(page.locator("#message")).to_contain_text("firstname 不能为空")
    expect(page.locator("#booking-rows tr")).to_have_count(0)


def test_change_price_updates_the_row(page):
    """改价：输入 500 → 点改价 → 列表里的价格变成 500。"""
    login(page)
    create_booking(page, totalprice="288")
    row = page.locator("#booking-rows tr").first
    row.locator(".price-input").fill("500")
    row.locator(".save-price").click()
    expect(page.locator("#message")).to_have_text("价格已保存")
    expect(row).to_contain_text("500")


def test_delete_removes_the_row(page):
    """删除：点删除后这一行消失，列表回到空。"""
    login(page)
    create_booking(page)
    page.locator("#booking-rows tr").first.locator(".delete").click()
    expect(page.locator("#message")).to_have_text("已删除")
    expect(page.locator("#booking-rows tr")).to_have_count(0)
