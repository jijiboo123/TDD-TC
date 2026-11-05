"""体检器对多语言的支持：Python 走 AST，Java / JS / TS / Go 走轻量正则规则。

这组用例证明两件事：
  1. 非 Python 的源码也能扫出"硬编码凭据 / 危险调用 / 调试残留"；
  2. 干净文件不会误报（有规则不等于乱报）。
"""

import allure

import scanner

pytestmark = allure.feature("体检器 · 多语言")


def write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_java_hardcoded_password_and_exec(tmp_path):
    target = write(tmp_path / "Demo.java", (
        'class Demo {\n'
        '    String password = "hunter2";\n'
        '    void run() { Runtime.getRuntime().exec(cmd); }\n'
        '}\n'
    ))
    findings, info, _ = scanner.collect(str(target), with_tests=False)

    kinds = [item.kind for item in findings]
    assert "硬编码凭据（Java）" in kinds
    assert "危险调用（Java）" in kinds
    assert info["target_file"] == "Demo.java"


def test_javascript_console_and_eval(tmp_path):
    target = write(tmp_path / "app.js", (
        'const token = "abcdef123";\n'
        'console.log("debug");\n'
        'eval(userInput);\n'
    ))
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    kinds = [item.kind for item in findings]

    assert "硬编码凭据（JavaScript）" in kinds
    assert "调试残留（JavaScript）" in kinds
    assert "危险调用（JavaScript）" in kinds


def test_go_exec_command(tmp_path):
    target = write(tmp_path / "main.go", (
        'package main\n'
        'import "os/exec"\n'
        'func main() { exec.Command("ls") }\n'
    ))
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    assert any(item.kind == "危险调用（Go）" for item in findings)


def test_clean_typescript_has_no_findings(tmp_path):
    target = write(tmp_path / "math.ts", "export const add = (a: number, b: number) => a + b;\n")
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    assert findings == []


def test_project_mode_counts_languages(tmp_path):
    write(tmp_path / "a.py", "value = 1\n")
    write(tmp_path / "b.js", "export const x = 1;\n")
    write(tmp_path / "c.go", "package main\n")
    write(tmp_path / "ignore.txt", "not source\n")

    _, info, _ = scanner.collect(str(tmp_path), with_tests=False)
    assert info["python_files"] == 1
    assert info["other_files"] == 2


def test_unsupported_extension_is_rejected(tmp_path):
    target = write(tmp_path / "notes.txt", "hello\n")
    try:
        scanner.collect(str(target), with_tests=False)
    except SystemExit as error:
        assert ".py" in str(error)
    else:
        raise AssertionError("未知后缀应当被拒绝")


# ---- 豁免注释：有意为之的写法不该被报 ----


def test_suppression_marker_hides_python_finding(tmp_path):
    target = write(tmp_path / "demo.py", (
        "def parse(text):\n"
        "    try:\n"
        "        return int(text)\n"
        "    except ValueError:  # scanner: ignore - 解析不了就走下面的兜底\n"
        "        pass\n"
        "    return 0\n"
    ))
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    assert findings == []


def test_without_marker_still_reports(tmp_path):
    target = write(tmp_path / "demo.py", (
        "def parse(text):\n"
        "    try:\n"
        "        return int(text)\n"
        "    except ValueError:\n"
        "        pass\n"
        "    return 0\n"
    ))
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    assert any(item.kind == "异常被吞掉" for item in findings)


def test_suppression_marker_works_for_js(tmp_path):
    target = write(tmp_path / "app.js", 'console.log("debug");  // scanner: ignore - 演示用的\n')
    findings, _, _ = scanner.collect(str(target), with_tests=False)
    assert findings == []

