"""环境自检：一条命令（或主页面启动时）看清"这台机器现在能不能跑这个项目"。

检查四类东西：
  1. Python 版本（要 3.11+）
  2. 接口层依赖（pytest / requests / allure-pytest）
  3. UI 层依赖（playwright 包 + Chromium 浏览器）
  4. Allure 报告依赖（Java + allure 命令）

用法：python check_env.py
GUI 里直接调用 collect_status() 拿结果，不用解析文本。
"""

import importlib.util
import os
import platform
import subprocess
import sys
from pathlib import Path

try:
    import winreg
except ImportError:      # 非 Windows 环境没有注册表
    winreg = None

MODULES = ("pytest", "requests", "allure_pytest", "ruff", "playwright")


def registry_env(name):
    """从注册表读环境变量：当前进程可能还没拿到刚设置的 JAVA_HOME/PATH。"""
    if winreg is None:
        return None
    locations = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    )
    for root, sub in locations:
        try:
            with winreg.OpenKey(root, sub) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except OSError:
            continue
    return None


def effective_path():
    """把进程 PATH 和注册表里的用户/系统 PATH 合起来，模拟"新开窗口"看到的环境。"""
    parts = []
    for chunk in (os.environ.get("PATH", ""), registry_env("Path") or ""):
        parts.extend(part for part in chunk.split(os.pathsep) if part)
    seen = set()
    unique = []
    for part in parts:
        key = part.rstrip("\\").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(part)
    return unique


def java_home():
    return os.environ.get("JAVA_HOME") or registry_env("JAVA_HOME")


def find_in_path(names):
    """在合并后的 PATH 里找命令（Windows 上 allure 是 allure.bat）。"""
    for folder in effective_path():
        for name in names:
            candidate = Path(folder) / name
            if candidate.exists():
                return candidate
    return None


def has_module(name):
    return importlib.util.find_spec(name) is not None


def chromium_path():
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
    folders = sorted(root.glob("chromium-*")) if root.exists() else []
    return folders[-1] if folders else None


def java_status():
    executable = None
    home = java_home()
    if home:
        candidate = Path(home) / "bin" / "java.exe"
        if candidate.exists():
            executable = candidate
    if executable is None:
        executable = find_in_path(["java.exe", "java"])
    if executable is None:
        return False, "找不到 java（JAVA_HOME 也未指向有效 JDK）"
    try:
        done = subprocess.run([str(executable), "-version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)
    text = (done.stderr or done.stdout or "").strip().splitlines()
    return done.returncode == 0, (text[0] if text else "")


def problems_from(status):
    problems = []
    if not status["python_ok"]:
        problems.append("升级 Python 到 3.11 以上")
    for name in ("pytest", "requests"):
        if not status["modules"][name]:
            problems.append(f"pip install -r requirements.txt（缺 {name}）")
    if not status["modules"]["allure_pytest"]:
        problems.append("pip install allure-pytest（Allure 报告）")
    if not (status["modules"]["playwright"] and status["chromium"]):
        problems.append("双击 安装UI依赖.bat（装 playwright + Chromium）")
    if not (status["java_ok"] and status["allure"]):
        problems.append("装 JDK + Allure CLI 才能看富报告（README 第 13 节）")
    return problems


def collect_status():
    """把检查结果收成一个字典，GUI 和命令行共用。"""
    chromium = chromium_path()
    java_ok, java_info = java_status()
    allure_cmd = find_in_path(["allure.bat", "allure.cmd", "allure.exe", "allure"])
    status = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "python_ok": sys.version_info >= (3, 11),
        "modules": {name: has_module(name) for name in MODULES},
        "chromium": chromium.name if chromium else None,
        "java_ok": java_ok,
        "java_info": java_info,
        "allure": str(allure_cmd) if allure_cmd else None,
    }
    status["core_ok"] = bool(status["python_ok"] and status["modules"]["pytest"] and status["modules"]["requests"])
    status["problems"] = problems_from(status)
    return status


def print_status(status):
    print("=" * 62)
    print("  软件测试可视化 · 环境自检")
    print("=" * 62)
    print(f"{'Python':<16}{status['python']:<24}{'✓' if status['python_ok'] else '✗ 需要 3.11+'}")
    print(f"{'操作系统':<14}{status['os'][:40]}")
    for name in ("pytest", "requests", "allure_pytest", "ruff", "playwright"):
        ok = status["modules"][name]
        mark = "✓" if ok else ("—  可选" if name in ("ruff", "playwright", "allure_pytest") else "✗")
        print(f"{name:<16}{'已安装' if ok else '未安装':<24}{mark}")
    print(f"{'Chromium':<16}{(status['chromium'] or '未下载'):<24}{'✓' if status['chromium'] else '✗ 可选'}")
    java_mark = "✓" if status["java_ok"] else "✗ 可选"
    print(f"{'Java':<16}{status['java_info'][:24]:<24}{java_mark}")
    print(f"{'allure 命令':<14}{'已就绪' if status['allure'] else '未找到':<24}{'✓' if status['allure'] else '✗ 可选'}")
    print("-" * 62)
    print("核心环境 OK：接口测试可以跑。" if status["core_ok"] else "核心依赖不全，先按下面的清单补：")
    if status["problems"]:
        print("\n待处理：")
        for index, item in enumerate(status["problems"], 1):
            print(f"  {index}. {item}")
    else:
        print("全部就绪（含 UI / Allure / 性能）。")
    print("=" * 62)


def main():
    status = collect_status()
    print_status(status)
    return 0 if status["core_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
