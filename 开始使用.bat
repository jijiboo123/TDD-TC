@echo off
rem ASCII-only launcher: cmd mangles UTF-8 Chinese in .bat files at codepage 936.
cd /d "%~dp0"
title Software Testing Visualizer

where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.11+ and add it to PATH.
  pause
  exit /b 1
)

python -c "import tkinter" >nul 2>nul
if errorlevel 1 (
  echo tkinter is not available in this Python. Starting the console menu instead.
  python start_menu.py
  exit /b 0
)

python tester_gui.py
if errorlevel 1 (
  echo.
  echo GUI exited with an error. Starting the console menu instead.
  python start_menu.py
)
exit /b 0
