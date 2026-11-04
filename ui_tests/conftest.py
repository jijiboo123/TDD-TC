"""UI 层夹具：起浏览器、每个用例一个干净页面，失败时自动留存现场。

为什么每个用例新建 context：context 之间 cookie / localStorage 完全隔离，
用例不会互相串登录态 —— 相当于接口测试里"每个用例前清空数据"。

失败时留下两样东西（都在 artifacts/ui/ 下）：
  - .png   失败瞬间的整页截图，能直接看到"卡在哪一步"；
  - .zip   Playwright trace，可用 `python -m playwright show-trace 文件` 逐步回放。
这样 CI 红了不用靠猜，也不用手动复现。
"""

import time
import warnings
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts" / "ui"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """把每个阶段的报告挂到用例上 —— teardown 阶段才判断得出这条到底过没过。"""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch()
        yield instance
        instance.close()


@pytest.fixture
def page(browser, base_url, request):
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    ui = context.new_page()
    ui.goto(f"{base_url}/")
    try:
        yield ui
    finally:
        report = getattr(request.node, "rep_call", None)
        if report is not None and report.failed:
            ARTIFACTS.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            name = request.node.name.replace("[", "_").replace("]", "")
            try:
                ui.screenshot(path=str(ARTIFACTS / f"{name}-{stamp}.png"), full_page=True)
                context.tracing.stop(path=str(ARTIFACTS / f"{name}-{stamp}.zip"))
            except Exception as error:
                # 页面已经崩了也要让原始失败信息露出来，别被留存逻辑盖住
                warnings.warn(f"失败现场保存失败：{error}", RuntimeWarning)
        else:
            context.tracing.stop()
        context.close()
