@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ==== 跑用例 + 生成 Allure 报告（需要 Java）====

if not defined JAVA_HOME (
  echo.
  echo [提示] 这个窗口里没有 JAVA_HOME。
  echo 本机 JDK 装在 D:\tools\jdk-25.0.5+8，环境变量是用户级的，新开窗口才生效。
  echo 关掉窗口重新双击一次；仍然不行就看 README 第 13 节。
  pause
  exit /b 1
)

where allure >nul 2>nul
if errorlevel 1 (
  echo.
  echo [提示] 找不到 allure 命令。
  echo 请确认 PATH 里有 D:\tools\allure-2.46.1\bin，然后重开窗口。
  pause
  exit /b 1
)

echo JAVA_HOME = %JAVA_HOME%
python -m pytest --alluredir=allure-results -q
echo.
echo ==== 生成并打开 Allure 报告（按 Ctrl+C 结束服务）====
call allure serve allure-results
pause
