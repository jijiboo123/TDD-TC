@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==== UI 测试（Playwright）====

python -c "import playwright" 2>nul
if errorlevel 1 goto noplaywright

python -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); p.chromium.launch().close(); p.stop()" 2>nul
if errorlevel 1 goto nobrowser

echo 环境检查通过，开始跑用例 ...
echo.
python -m pytest ui_tests -v
echo.
if errorlevel 1 (
  echo [结果] 有失败用例，把上面的红字发我。
) else (
  echo [结果] 全部通过。
)
pause
exit /b 0

:noplaywright
echo.
echo [提示] 还没装 playwright 包。
echo 请先双击本目录下的「安装UI依赖.bat」，装完再运行这个。
pause
exit /b 1

:nobrowser
echo.
echo [提示] playwright 装了，但 Chromium 浏览器没装好。
echo 请先双击本目录下的「安装UI依赖.bat」把它补上。
pause
exit /b 1
