@echo off
cd /d "%~dp0"
echo [1/2] install playwright package ...
python -m pip install playwright
if errorlevel 1 goto failed
echo.
echo [2/2] download chromium (about 300MB, be patient) ...
python -m playwright install chromium
if errorlevel 1 goto failed
echo.
echo Done. Next: double-click the launcher (start menu) and choose option 2.
pause
exit /b 0

:failed
echo.
echo [error] step failed. Send the last lines to the assistant.
pause
exit /b 1