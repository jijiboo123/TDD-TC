"""环境自检：一条命令看清"这台机器现在能不能跑这个项目"。

检查四类东西：
  1. Python 版本（要 3.11+）
  2. 接口层依赖（pytest / requests / allure-pytest）
  3. UI 层依赖（playwright 包 + Chromium 浏览器）
  4. Allure 报告依赖（Java + allure 命令）

用法：python check_env.py
退出码：接口层依赖缺失时返回 1，其余只提示不阻断。
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
    first = text[0] if text else ""
    return done.returncode == 0, first


def main():
    problems = []
    print("=" * 62)
    print("  软件测试可视化 · 环境自检")
    print("=" * 62)

    version = platform.python_version()
    python_ok = sys.version_info >= (3, 11)
    print(f"{'Python':<16}{version:<24}{'✓' if python_ok else '✗ 需要 3.11+'}")
    if not python_ok:
        problems.append("升级 Python 到 3.11 以上")

    print(f"{'操作系统':<14}{platform.platform()[:40]}")

    for module, purpose in (("pytest", "跑测试"), ("requests", "发请求"), ("allure_pytest", "Allure 报告")):
        ok = has_module(module)
        print(f"{module:<16}{'已安装' if ok else '未安装':<24}{'✓' if ok else '✗'}")
        if not ok and module in ("pytest", "requests"):
            problems.append(f"pip install -r requirements.txt（缺 {module}）")

    ruff_ok = has_module("ruff")
    print(f"{'ruff':<16}{'已安装' if ruff_ok else '未安装':<24}{'✓' if ruff_ok else '—  可选'}")
    if not ruff_ok:
        problems.append("pip install ruff（静态检查，可选）")

    playwright_ok = has_module("playwright")
    browser = chromium_path()
    print(f"{'playwright':<16}{'已安装' if playwright_ok else '未安装':<24}{'✓' if playwright_ok else '✗ 可选'}")
    print(f"{'Chromium':<16}{(browser.name if browser else '未下载'):<24}{'✓' if browser else '✗ 可选'}")
    if not (playwright_ok and browser):
        problems.append("双击 安装UI依赖.bat（装 playwright + Chromium）")

    java_ok, java_info = java_status()
    print(f"{'Java':<16}{(java_info[:24] if java_ok else java_info):<24}{'✓' if java_ok else '✗ 可选'}")
    allure_cmd = find_in_path(["allure.bat", "allure.cmd", "allure.exe", "allure"])
    print(f"{'allure 命令':<14}{'已就绪' if allure_cmd else '未找到':<24}{'✓' if allure_cmd else '✗ 可选'}")
    if not (java_ok and allure_cmd):
        problems.append("装 JDK + Allure CLI 才能看富报告（README 第 13 节）")

    print("-" * 62)
    core_ok = python_ok and has_module("pytest") and has_module("requests")
    if core_ok:
        print("核心环境 OK：接口测试可以跑。")
    else:
        print("核心依赖不全，先按下面的清单补：")
    if problems:
        print("\n待处理：")
        for index, item in enumerate(problems, 1):
            print(f"  {index}. {item}")
    else:
        print("全部就绪（含 UI / Allure / 性能）。")
    print("=" * 62)
    return 0 if core_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
