@echo off
:: ReadSite 自动化配置脚本 - Windows 入口
:: 用法: scripts\setup.bat
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 解析脚本自身目录（支持从任意目录调用）
set "SCRIPT_DIR=%~dp0"
:: 去除末尾反斜杠
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: ── 查找 Python 3.12 ──────────────────────────────────────────────────────────
set "PYTHON_CMD="
:: 优先使用 py -3.12 定位
py -3.12 -c "exit()" >nul 2>&1
if !errorlevel! equ 0 (
    for /f "delims=" %%i in ('py -3.12 -c "import sys; print(sys.executable)"') do set "PYTHON_CMD=%%i"
)

:: 若 py -3.12 不可用，解析 py -0p 输出
if not defined PYTHON_CMD (
    for /f "tokens=1* delims= " %%a in ('py -0p 2^>nul ^| findstr /R "3\.12"') do (
        if not defined PYTHON_CMD (
            :: 跳过前面的版本标记，从第二个字段开始拼接完整路径
            set "LINE=%%b"
            :: 去除可能的尾部空格
            for /f "tokens=*" %%p in ("!LINE!") do set "PYTHON_CMD=%%p"
        )
    )
)

if not defined PYTHON_CMD (
    echo.
    echo   X 错误: 未找到 Python 3.12.x
    echo.
    echo   请先安装 Python 3.12:
    echo     https://www.python.org/downloads/
    echo.
    echo   安装时请勾选 "Add Python to PATH" 选项。
    echo.
    pause
    exit /b 1
)

echo.
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do echo   OK 找到 Python: %%v
echo.

:: ── 调用主配置脚本，传入 Python 可执行文件路径 ────────────────────────────────
"!PYTHON_CMD!" "%SCRIPT_DIR%\setup.py" "!PYTHON_CMD!" %*
