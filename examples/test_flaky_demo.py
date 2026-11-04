"""两条"偶发失败"的示例用例，用来看清重试到底做了什么。

它们不算项目资产：默认 pytest 只扫 tests/ 目录，所以不会污染回归结果。
手动跑：

    python -m pytest examples/ -q
"""

import random

import pytest


@pytest.mark.flaky(reruns=2, delay=0.05)
def test_first_attempt_fails_on_purpose():
    """第一次故意失败 —— 每次跑都能看到 RERUN 长什么样（确定性演示）。"""
    test_first_attempt_fails_on_purpose.calls += 1
    assert test_first_attempt_fails_on_purpose.calls > 1, "第一次故意失败，第二次正常"


test_first_attempt_fails_on_purpose.calls = 0


@pytest.mark.flaky(reruns=5, delay=0.05)
def test_sometimes_slow_response():
    """10% 概率"超时" —— 模拟真实世界里最让人头疼的那类偶发失败。"""
    assert random.random() > 0.1, "模拟一次瞬时抖动"
