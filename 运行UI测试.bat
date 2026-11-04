@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.11+ and add it to PATH.
  pause
  exit /b 1
)
python -m pytest ui_tests -v
if errorlevel 1 echo [result] some UI cases failed - scroll up for details.
pause
exit /b 0