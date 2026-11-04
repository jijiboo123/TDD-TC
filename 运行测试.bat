@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==== 接口测试（pytest）====
python -m pytest
echo.
pause
