@echo off
cd /d "%~dp0"
echo ==== api-testing-demo ====
echo.
python -m pytest
echo.
echo ==== done. press any key ====
pause >nul
