"""一条命令：跑用例 → 带上历史 → 生成 Allure 趋势报告。

Allure 的 Trend 图不是凭空来的：它读的是报告目录里的 `history/`。
所以每次生成前，要把上一次的 `allure-report/history` 拷进 `allure-results/`，
Allure 生成时就会把它带进新报告，跑得次数越多，折线越长。

用法：
    python allure_run.py            # 生成报告
    python allure_run.py --open     # 生成后起本地服务打开
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "allure-results"
REPORT = ROOT / "allure-report"


def run(command):
    print("$ " + " ".join(str(part) for part in command))
    return subprocess.run(command, cwd=ROOT, check=False)


def find_allure():
    """allure 在 Windows 上是 allure.bat，subprocess 直接调会失败，所以走 cmd /c。"""
    path = shutil.which("allure")
    if not path:
        return None
    if path.lower().endswith((".bat", ".cmd")):
        return ["cmd", "/c", path]
    return [path]


def main():
    parser = argparse.ArgumentParser(description="跑用例并生成带历史趋势的 Allure 报告")
    parser.add_argument("--open", action="store_true", help="生成后起服务打开浏览器")
    args = parser.parse_args()

    if not os.environ.get("JAVA_HOME"):
        print("提示：没有 JAVA_HOME，Allure 可能起不来（README 第 13 节有安装说明）")

    RESULTS.mkdir(exist_ok=True)
    history = REPORT / "history"
    if history.exists():
        target = RESULTS / "history"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(history, target)
        print("已带入上一次的趋势数据")
    else:
        print("首次运行：还没有历史数据，这是趋势图的第一个点")

    tests = run([sys.executable, "-m", "pytest", "--alluredir", str(RESULTS), "-q"])
    if tests.returncode not in (0, 1):
        print("pytest 没能正常启动")
        return tests.returncode

    allure = find_allure()
    if allure is None:
        print("找不到 allure 命令：确认 D:\\tools\\allure-2.46.1\\bin 在 PATH 里（新开窗口才生效）")
        return 2

    result = run(allure + ["generate", str(RESULTS), "-o", str(REPORT), "--clean"])
    if result.returncode != 0:
        print("Allure 生成失败")
        return result.returncode

    print(f"报告目录：{REPORT}")
    print(f"本地查看：allure open \"{REPORT}\"   或者双击 生成Allure报告.bat")
    if args.open:
        run(allure + ["open", str(REPORT)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
