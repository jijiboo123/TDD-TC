@echo off
rem ASCII-only launcher. The GUI is started through launch_gui.vbs so no console window stays open.
cd /d "%~dp0"

if exist "launch_gui.vbs" (
  wscript //nologo "launch_gui.vbs"
  exit /b 0
)

rem Fallback: run with console visible (helps when VBS is blocked by policy).
python tester_gui.py
if errorlevel 1 pause
exit /b 0
