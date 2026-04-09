@echo off
:: ReadSite 快速开发启动脚本 - Windows
:: 功能: 执行数据库迁移，启动 runserver
:: 用法: scripts\dev.bat
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: 项目根目录 = scripts 目录的上级
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"

set "VENV_PYTHON=%PROJECT_ROOT%\venv\Scripts\python.exe"

:: ── 检查虚拟环境 ──────────────────────────────────────────────────────────────
if not exist "%VENV_PYTHON%" (
    echo.
    echo   X 未找到虚拟环境: %PROJECT_ROOT%\venv\
    echo.
    echo   请先运行配置脚本完成初始化:
    echo     scripts\setup.bat
    echo.
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"

echo.
echo   Running makemigrations...
"%VENV_PYTHON%" manage.py makemigrations

echo.
echo   Running migrate...
"%VENV_PYTHON%" manage.py migrate

echo.
echo   Starting development server...
echo   Visit: http://127.0.0.1:8000
echo   API:   http://127.0.0.1:8000/api/docs/
echo   Press Ctrl+C to stop
echo.
"%VENV_PYTHON%" manage.py runserver
