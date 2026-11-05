"""项目控制台：双击 `开始使用.bat` 会进到这里。

为什么不用 bat 写菜单：cmd 读批处理时用控制台代码页解码，
双击的窗口默认是 936（GBK），而 bat 文件是 UTF-8，多字节字符一旦
跨过读取缓冲区就会裂开——表现就是中文乱码、甚至半行被当成命令执行。
Python 直接往控制台写 Unicode，没有这个问题。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

MENU = """
============================================================
   软件测试可视化 · 一键控制台
============================================================
   1. 环境自检（第一次先跑这个）      6. 看语句覆盖率
   2. 跑接口测试（92 条）             7. 跑性能基线
   3. 跑 UI 测试（9 条，需要浏览器）   8. 跑真实公开 API（联网）
   4. 生成 HTML 报告并打开            9. 打开项目文件夹
   5. 生成 Allure 富报告（需要 Java）  0. 退出
============================================================"""


def clear():
    if sys.stdout.isatty():
        print("\n" * 40, end="")     # 不用 os.system("cls")：省一次 shell 调用，也不会被静态检查当成命令执行风险


def pause():
    try:
        input("\n按回车回到菜单...")
    except EOFError:
        raise SystemExit(0)


def run(args, extra_env=None):
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    print()
    result = subprocess.run(args, cwd=ROOT, env=env)
    return result.returncode


def action_env():
    import check_env
    check_env.main()
    pause()


def action_api():
    run([sys.executable, "-m", "pytest"])
    pause()


def action_ui():
    run([sys.executable, "-m", "pytest", "ui_tests", "-q"])
    pause()


def action_report():
    run([sys.executable, "reports.py", "--open"])
    pause()


def action_allure():
    code = run([sys.executable, "allure_run.py"])
    if code == 0:
        print("\n正在打开报告服务（关掉那个窗口即停止）...")
        subprocess.Popen(["cmd", "/c", "start", "Allure 报告", "cmd", "/k", "allure open allure-report"], cwd=ROOT)
    else:
        print("\n报告没生成成功，先跑第 1 项环境自检。")
    pause()


def action_coverage():
    run([sys.executable, "coverage_simple.py"])
    pause()


def action_perf():
    run([sys.executable, "perf_load.py"])
    pause()


def action_live():
    run([sys.executable, "-m", "pytest", "live_tests", "-q"], {"LIVE_API": "1"})
    pause()


def action_folder():
    os.startfile(str(ROOT))      # noqa: S606 - 打开资源管理器，仅 Windows


ACTIONS = {
    "1": action_env,
    "2": action_api,
    "3": action_ui,
    "4": action_report,
    "5": action_allure,
    "6": action_coverage,
    "7": action_perf,
    "8": action_live,
    "9": action_folder,
}


def main():
    while True:
        clear()
        print(MENU)
        try:
            choice = input("\n输入序号后回车：").strip()
        except EOFError:
            return 0
        if choice in ("", "0"):
            return 0
        action = ACTIONS.get(choice)
        if action is None:
            print("没有这个选项，重新输入。")
            continue
        action()


if __name__ == "__main__":
    raise SystemExit(main())
