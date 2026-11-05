"""体检器的"跑测试"结果要分清楚：真实用例失败 vs 依赖没装导致收集失败。

背景：用户把整个工作区当成被测项目扫，pytest 在里面收集到一堆别的项目的测试，
依赖没装 → 每条 ERROR 都被当成"高危用例失败"，刷屏且误导。
"""

import allure

import scanner

pytestmark = allure.feature("体检器 · 测试结果分类")


def test_collection_failure_is_one_finding(tmp_path):
    """依赖没装：只报一条"测试无法收集"，而不是每条 ERROR 都算缺陷。"""
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "test_broken.py").write_text(
        "import definitely_missing_module_xyz\n\ndef test_ok():\n    assert True\n",
        encoding="utf-8",
    )
    findings, _, result = scanner.collect(str(tmp_path), with_tests=True)

    assert result["collection_failed"] is True
    kinds = [item.kind for item in findings]
    assert kinds.count("测试无法收集") == 1
    assert "测试失败" not in kinds


def test_real_failure_is_high_severity(tmp_path):
    """真实用例失败：是一条高危的"测试失败"，带用例位置。"""
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "test_fail.py").write_text("def test_x():\n    assert 1 == 2\n", encoding="utf-8")
    findings, _, result = scanner.collect(str(tmp_path), with_tests=True)

    assert result["collection_failed"] is False
    assert result["exit_code"] == 1
    failures = [item for item in findings if item.kind == "测试失败"]
    assert len(failures) == 1
    assert failures[0].severity == "高"


def test_parse_test_failures_is_limited():
    """失败很多时最多列 20 条，避免刷屏。"""
    output = "\n".join(f"FAILED tests/test_{i}.py::test_x - assert {i}" for i in range(30))
    findings = scanner.parse_test_failures(output, limit=20)
    assert len(findings) == 20


def test_parse_collection_error_reports_reason():
    output = (
        "ERROR collecting tests/test_main.py\n"
        "ModuleNotFoundError: No module named 'aider'\n"
    )
    findings = scanner.parse_collection_error(output)
    assert len(findings) == 1
    assert findings[0].severity == "中"
    assert "No module named" in findings[0].detail


def test_multi_project_directory_is_flagged(tmp_path):
    """一个目录里塞了多个项目：提示用户选具体子目录。"""
    for name in ("proj_a", "proj_b"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        (folder / "main.py").write_text("value = 1\n", encoding="utf-8")

    _, info, _ = scanner.collect(str(tmp_path), with_tests=False)
    assert info["multi_project"] is True
    assert info["sub_projects"] == 2
    assert info["sub_project_list"] == ["proj_a", "proj_b"]


def test_workspace_never_runs_other_projects_tests(tmp_path):
    """真正的保护：工作区目录即使勾了跑测试，也不去跑别人家的测试。"""
    for name in ("proj_a", "proj_b"):
        folder = tmp_path / name
        folder.mkdir()
        (folder / "requirements.txt").write_text("pytest\n", encoding="utf-8")
        # 故意让"别人家"的测试必然失败，验证根本不会被执行
        (folder / "test_broken.py").write_text("def test_x():\n    assert 1 == 2\n", encoding="utf-8")

    findings, info, result = scanner.collect(str(tmp_path), with_tests=True)

    assert result["ran"] is False
    assert result["skipped_workspace"] is True
    assert "测试失败" not in [item.kind for item in findings]
    not_run = [item for item in findings if item.kind == "测试未运行"]
    assert len(not_run) == 1
    assert "proj_a" in not_run[0].detail

