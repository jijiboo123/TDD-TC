@echo off
cd /d "%~dp0"
echo ==== run tests + build report ====
python reports.py --open
echo.
echo ==== statement coverage ====
python coverage_simple.py
echo.
pause