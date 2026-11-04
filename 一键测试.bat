@echo off
cd /d "%~dp0"
echo ==== run tests + build report ====
python reports.py --open
echo.
pause >nul
