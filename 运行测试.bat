@echo off
rem ASCII-only: cmd mangles UTF-8 Chinese batch files when console codepage is 936.
cd /d "%~dp0"
python -m pytest
pause
exit /b 0