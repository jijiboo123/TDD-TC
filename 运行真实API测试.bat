@echo off
cd /d "%~dp0"
set LIVE_API=1
python -m pytest live_tests -v
set LIVE_API=
echo.
echo These cases use the public internet; slow is normal. Offline = skipped.
pause
exit /b 0