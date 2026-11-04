@echo off
rem ASCII-only wrapper: cmd's batch parser mangles UTF-8 Chinese when the console codepage is 936.
rem The real menu lives in start_menu.py so Chinese output is safe.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.11+ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)
python start_menu.py
if errorlevel 1 pause
exit /b 0
