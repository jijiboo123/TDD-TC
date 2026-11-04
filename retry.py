"""失败重试插件（零依赖）—— 专治"偶发失败"（flaky test）。

为什么要重试：网络抖动、时序竞争造成的偶发失败，重跑一次就过了。如果每次
CI 都随机变红，团队就会开始"习惯性忽略红叉"，测试也就废了。

但重试是止痛药，不是消炎药：
  - 只给"已知偶发"的用例打标记，默认一个用例都不重试；
  - 每次重试都会在末尾"重试记录"里点名，提醒你回头查根因；
  - 真缺陷（每次必现）不会被重试救活，这是它的安全边界。

用法：

    @pytest.mark.flaky(reruns=2, delay=0.3)
    def test_something_networky():
        ...

自动加载：conftest.py 里的 pytest_plugins = ["retry"]。

实现要点（面试也爱问）：pytest 正常跑一个用例 = setup → call → teardown。
重试的做法是自己接管这个协议，把"跑一个用例"重复执行，最后只把**最后一轮**
的结果交给 pytest 记录，中间的失败不会污染统计。
"""

import time

import pytest
from _pytest.runner import runtestprotocol

_retried = []   # [(nodeid, 重试次数, 最终是否通过)]


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "flaky(reruns=2, delay=0.3): 失败后自动重试，只用于已知的偶发失败",
    )


def pytest_sessionstart(session):
    _retried.clear()


def _flaky_settings(item):
    """没打 flaky 标记就返回 None —— 普通用例一次都不重试。"""
    marker = item.get_closest_marker("flaky")
    if marker is None:
        return None
    return int(marker.kwargs.get("reruns", 2)), float(marker.kwargs.get("delay", 0.3))


def _notify(item, message):
    """直接写到 pytest 终端，让"重试"这件事在输出里看得见。"""
    reporter = item.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line(message, yellow=True)


def _call_report(reports):
    for report in reports:
        if report.when == "call":
            return report
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, nextitem):
    settings = _flaky_settings(item)
    if settings is None:
        return None      # 交给 pytest 默认流程，一个字符都不改

    reruns, delay = settings
    ihook = item.ihook
    ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)

    reports = runtestprotocol(item, log=False, nextitem=nextitem)
    attempt = 0
    while attempt < reruns:
        report = _call_report(reports)
        if report is None or not report.failed:
            break        # 过了，或者夹具就没起来（那种失败重试也没用）
        attempt += 1
        _notify(item, f"  RERUN {item.nodeid}：第 {attempt} 次没通过，{delay}s 后重试")
        time.sleep(delay)
        reports = runtestprotocol(item, log=False, nextitem=nextitem)

    # 只把最后一轮的结果交给 pytest，中间失败不进统计
    for report in reports:
        ihook.pytest_runtest_logreport(report=report)
    ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

    if attempt:
        final = _call_report(reports)
        _retried.append((item.nodeid, attempt, final is not None and final.passed))
    return True


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """测试结束后把"谁靠重试才过的"单独列出来。"""
    if not _retried:
        return
    terminalreporter.write_sep("-", "重试记录（只对打了 flaky 标记的用例生效）")
    for nodeid, times, passed in _retried:
        verdict = f"重试 {times} 次后通过" if passed else f"重试 {times} 次仍失败"
        terminalreporter.write_line(f"  {nodeid}  {verdict}")
    rescued = sum(1 for _, _, passed in _retried if passed)
    if rescued:
        terminalreporter.write_line(f"  共 {rescued} 个用例靠重试变绿 —— 记下来查根因，别长期留着")
