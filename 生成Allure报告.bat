@echo off
cd /d "%~dp0"
python allure_run.py
if errorlevel 1 (
  echo.
  echo [error] report failed. Run the launcher and choose option 1.
  pause
  exit /b 1
)
echo.
echo Opening report server ... close its window to stop.
start "Allure Report" cmd /k allure open allure-report
exit /b 0