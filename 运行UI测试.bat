@echo off
cd /d "%~dp0"
echo ==== UI tests (Playwright) ====
python -m pytest ui_tests -v
echo.
pause >nul
