@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==== 真实公开 API 测试（dummyjson.com，需要联网）====
set LIVE_API=1
python -m pytest live_tests -v
echo.
echo 提示：这些用例走公网，偶尔慢一点是正常的；连不上会自动 skip。
pause
