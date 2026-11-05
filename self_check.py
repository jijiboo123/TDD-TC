"""项目自检：一条命令回答"这个项目现在还是不是好的"。

检查 8 件事：
  1. 环境        Python 版本 + 关键依赖
  2. 结构        必需的文件/目录是否齐全
  3. 静态检查    ruff（装了才查）
  4. 自己扫自己  体检器扫本项目，不允许有高危
  5. 接口测试    跑 pytest，读 junit 统计
  6. UI 测试     Playwright（没装浏览器就跳过）
  7. 覆盖率      零依赖覆盖率工具，默认门槛 90%
  8. 文档数字    README / 测试方案里写的用例数，必须和实际一致
  9. 入口自检    主页面能不能正常构建（--selftest）

用法：
    python self_check.py                 # 全部检查
    python self_check.py --quick         # 跳过 UI（没浏览器时更快）
    python self_check.py --json out.json # 结果另存
    python self_check.py --min-coverage 80
"""

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT_XML = ROOT / "report.xml"

REQUIRED = (
    "mock_server.py", "conftest.py", "pytest.ini", "requirements.txt",
    "tests", "ui_tests", "live_tests", "schema", "web", "docs",
    "README.md", "CHANGELOG.md",
    "开始使用.bat", "launch_gui.vbs", "start_menu.py", "tester_gui.py", "check_env.py",
    ".github/workflows/test.yml",
)


def run(command, timeout=300):
    """跑子进程，统一 UTF-8 解码，返回 (退出码, 输出)。"""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"超过 {timeout} 秒未结束"
    except OSError as error:
        return 127, str(error)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def check_environment():
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    ok = sys.version_info >= (3, 11)
    return ok, f"Python {version}" + ("" if ok else "（需要 3.11+）")


def check_structure():
    missing = [name for name in REQUIRED if not (ROOT / name).exists()]
    if missing:
        return False, "缺少：" + "、".join(missing)
    return True, f"{len(REQUIRED)} 项齐全"


def check_ruff():
    code, output = run([sys.executable, "-m", "ruff", "check", "."], timeout=120)
    if code == 127 or "No module named" in output:
        return None, "未安装 ruff（跳过）"
    if code != 0:
        return False, output.strip().splitlines()[-1] if output.strip() else "ruff 报错"
    return True, "0 告警"


def check_self_scan():
    sys.path.insert(0, str(ROOT))
    import scanner  # 同目录导入

    findings, info, _ = scanner.collect(str(ROOT), with_tests=False)
    high = [item for item in findings if item.severity == "高"]
    detail = f"{info['python_files']} 个 Python 文件，高危 {len(high)} / 共 {len(findings)} 条"
    if high:
        detail += "；首个：" + f"{high[0].path}:{high[0].line} {high[0].kind}"
    return not high, detail


def parse_junit(path):
    tree = ET.parse(path)
    suite = tree.getroot()
    if suite.tag == "testsuites":
        suite = suite.find("testsuite")
    return {key: int(suite.get(key, 0)) for key in ("tests", "failures", "errors", "skipped")}


def check_api_tests():
    code, output = run([sys.executable, "-m", "pytest", "-q", "--junitxml", str(REPORT_XML)], timeout=900)
    if not REPORT_XML.exists():
        return False, "没有生成 junit 报告", {}
    stats = parse_junit(REPORT_XML)
    failed = stats["failures"] + stats["errors"]
    ok = code == 0 and failed == 0
    detail = f"{stats['tests']} 条：通过 {stats['tests'] - stats['skipped'] - failed}，跳过 {stats['skipped']}，失败 {failed}"
    return ok, detail, stats


def check_ui_tests():
    code, output = run([sys.executable, "-m", "pytest", "ui_tests", "-q"], timeout=600)
    if code == 127 or "No module named 'playwright'" in output:
        return None, "未安装 playwright（跳过）"
    if "executable doesn't exist" in output.lower():
        return None, "Chromium 未安装（跳过）"
    last = [line for line in output.strip().splitlines() if "passed" in line or "failed" in line]
    return code == 0, last[-1].strip("= ") if last else output.strip().splitlines()[-1]


def check_coverage(min_ratio):
    code, output = run([sys.executable, "coverage_simple.py"], timeout=300)
    match = re.search(r"覆盖率:\s*([\d.]+)%", output)
    if not match:
        return False, "没解析到覆盖率"
    ratio = float(match.group(1))
    return ratio >= min_ratio, f"{ratio:.1f}%（门槛 {min_ratio:.0f}%）"


def doc_numbers():
    """从 README 和测试方案里提取"接口 N 个用例""合计 N 个用例"。"""
    found = {}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    plan_path = ROOT / "docs" / "测试方案.md"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""

    match = re.search(r"接口\s*(\d+)\s*个用例", readme)
    if match:
        found["readme_api"] = int(match.group(1))
    match = re.search(r"合计\s*\*\*(\d+)\s*个用例\*\*", plan)
    if match:
        found["plan_total"] = int(match.group(1))
    match = re.search(r"参数化用例.*?(\d+)\s*个用例.*?(\d+)\s*个测试函数", readme, re.S)
    if match:
        found["readme_total"] = int(match.group(1))
        found["readme_functions"] = int(match.group(2))
    return found


def count_ui_tests():
    """数 ui_tests 里的测试函数（用 AST，不 import playwright，没装浏览器也能数）。"""
    import ast

    total = 0
    for path in (ROOT / "ui_tests").glob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        total += sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )
    return total


def check_docs(stats, ui_stats):
    numbers = doc_numbers()
    api_total = stats.get("tests", 0)
    ui_total = count_ui_tests()
    total = api_total + ui_total
    problems = []

    if numbers.get("readme_api") not in (None, api_total):
        problems.append(f"README 写接口 {numbers['readme_api']} 条，实际 {api_total} 条")
    if numbers.get("plan_total") not in (None, total):
        problems.append(f"测试方案写合计 {numbers['plan_total']} 条，实际 {total} 条")
    if numbers.get("readme_total") not in (None, total):
        problems.append(f"README 写合计 {numbers['readme_total']} 条，实际 {total} 条")

    detail = f"接口 {api_total} + UI {ui_total} = {total} 条"
    if problems:
        return False, detail + "；" + "；".join(problems)
    return True, detail + "，文档与代码一致"


def check_gui():
    code, output = run([sys.executable, "tester_gui.py", "--selftest"], timeout=120)
    ok = code == 0 and "gui ok" in output
    return ok, "主页面可构建" if ok else (output.strip().splitlines()[-1] if output.strip() else "启动失败")


def check_git():
    """未提交改动只是提醒，不算质量问题——开发中本来就会有。"""
    code, output = run(["git", "status", "--short"], timeout=60)
    if code != 0:
        return None, "不是 git 仓库（跳过）"
    dirty = [line for line in output.strip().splitlines() if line.strip()]
    if dirty:
        return None, f"有 {len(dirty)} 个未提交改动（提醒，不算失败）"
    return True, "工作区干净"


def main():
    parser = argparse.ArgumentParser(description="软件测试可视化 · 项目自检")
    parser.add_argument("--quick", action="store_true", help="跳过 UI 用例")
    parser.add_argument("--min-coverage", type=float, default=90.0, help="覆盖率门槛，默认 90")
    parser.add_argument("--json", help="把结果另存为 JSON")
    args = parser.parse_args()

    results = []

    def record(name, outcome, detail=""):
        ok, detail = outcome if isinstance(outcome, tuple) else (outcome, detail)
        results.append({"name": name, "ok": ok, "detail": detail})
        # 用 ASCII 标记：Windows 控制台是 GBK，✓/✗ 在重定向到文件时会直接抛 UnicodeEncodeError
        mark = "[OK]" if ok else ("[--]" if ok is None else "[!!]")
        print(f"  {mark:<5}{name:<10}{detail}")

    print("=" * 70)
    print("  软件测试可视化 · 项目自检")
    print("=" * 70)

    record("环境", check_environment())
    record("结构", check_structure())
    record("ruff", check_ruff())
    record("自扫", check_self_scan())

    stats = {}
    ok, detail, stats = check_api_tests()
    record("接口测试", (ok, detail))

    if args.quick:
        record("UI 测试", (None, "已按 --quick 跳过"))
        ui_stats = {}
    else:
        ui_ok, ui_detail = check_ui_tests()
        record("UI 测试", (ui_ok, ui_detail))
        ui_stats = {"ok": ui_ok}

    record("覆盖率", check_coverage(args.min_coverage))
    record("文档数字", check_docs(stats, ui_stats))
    record("入口自检", check_gui())
    record("git", check_git())

    hard_fail = [item for item in results if item["ok"] is False]
    passed = sum(1 for item in results if item["ok"] is True)
    print("-" * 70)
    if hard_fail:
        print(f"未通过：{len(hard_fail)} 项 / 共 {len(results)} 项")
        for item in hard_fail:
            print(f"  [!!] {item['name']}：{item['detail']}")
    else:
        print(f"全部通过：{passed} 项检查")

    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"结果已写入 {args.json}")

    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
