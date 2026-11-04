@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 软件测试可视化 · 控制台

:menu
cls
echo ============================================================
echo    软件测试可视化 · 一键控制台
echo ============================================================
echo    1. 环境自检（第一次先跑这个）
echo    2. 跑接口测试（92 条）
echo    3. 跑 UI 测试（9 条，需要浏览器）
echo    4. 生成 HTML 报告并打开
echo    5. 生成 Allure 富报告（需要 Java）
echo    6. 看语句覆盖率
echo    7. 跑性能基线（并发梯度 p95/p99）
echo    8. 跑真实公开 API（需要联网）
echo    9. 打开项目文件夹
echo    0. 退出
echo ============================================================
set "choice="
set /p "choice=输入序号后回车："
if not defined choice goto end

if "%choice%"=="1" goto env
if "%choice%"=="2" goto api
if "%choice%"=="3" goto ui
if "%choice%"=="4" goto report
if "%choice%"=="5" goto allure
if "%choice%"=="6" goto coverage
if "%choice%"=="7" goto perf
if "%choice%"=="8" goto live
if "%choice%"=="9" goto folder
if "%choice%"=="0" goto end

echo.
echo 没有这个选项，重新输入。
timeout /t 2 >nul
goto menu

:env
cls
python check_env.py
echo.
pause
goto menu

:api
cls
python -m pytest
echo.
pause
goto menu

:ui
cls
python -m pytest ui_tests -q
echo.
pause
goto menu

:report
cls
python reports.py --open
echo.
pause
goto menu

:allure
cls
python allure_run.py
if errorlevel 1 (
  echo.
  echo 报告没生成成功，先看第 1 项环境自检。
  pause
  goto menu
)
echo.
echo 正在打开报告服务（关闭那个窗口即停止）...
start "Allure 报告" cmd /k allure open allure-report
goto menu

:coverage
cls
python coverage_simple.py
echo.
pause
goto menu

:perf
cls
python perf_load.py
echo.
pause
goto menu

:live
cls
set "LIVE_API=1"
python -m pytest live_tests -q
set "LIVE_API="
echo.
pause
goto menu

:folder
start "" explorer "%~dp0"
goto menu

:end
exit /b 0
