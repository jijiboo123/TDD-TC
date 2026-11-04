@echo off
cd /d "%~dp0"
echo ==== step 1/2 : run tests ====
python -m pytest
echo.
echo ==== step 2/2 : build report ====
python report.py --open
pause >nul
