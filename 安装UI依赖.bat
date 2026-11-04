@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==========================================
echo  安装 UI 测试环境（Playwright + Chromium）
echo  需要联网，第一次约 300MB，请耐心等待
echo ==========================================
echo.

echo [1/3] 检查 Python ...
python --version
if errorlevel 1 goto nopython

echo.
echo [2/3] 安装 playwright 包 ...
python -m pip install playwright
if errorlevel 1 goto failed

echo.
echo [3/3] 下载 Chromium 浏览器（约 300MB，没有进度条也别关窗口）...
python -m playwright install chromium
if errorlevel 1 goto failed

echo.
echo ==========================================
echo  安装完成！接下来双击 运行UI测试.bat
echo ==========================================
pause
exit /b 0

:nopython
echo.
echo [错误] 没有找到 python 命令。
echo 请先安装 Python 3.11 或以上版本，安装时勾选 "Add python.exe to PATH"。
pause
exit /b 1

:failed
echo.
echo [错误] 上一步失败了。把窗口最后几行发给我，我按报错给解法。
pause
exit /b 1
