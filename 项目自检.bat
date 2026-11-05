@echo off
rem ASCII-only launcher for the project self-check.
cd /d "%~dp0"
python self_check.py
echo.
pause
