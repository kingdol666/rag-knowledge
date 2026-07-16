@echo off
chcp 65001 >nul 2>&1

REM ============================================================
REM  ragctl.bat — RAG Knowledge Platform CLI Launcher (Windows)
REM ============================================================
REM Usage: ragctl <command> [options]
REM   First run: ragctl setup   (one-click deployment)
REM ============================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "COMMAND_DIR=%ROOT%\command"

REM Auto-install CLI deps if missing
if not exist "%COMMAND_DIR%\node_modules" (
    echo   [setup] Installing ragctl dependencies...
    cd /d "%COMMAND_DIR%"
    call npm install --silent >nul 2>&1
)

REM Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed or not in PATH
    echo Install from: https://nodejs.org/
    exit /b 1
)

REM Run ragctl
node "%COMMAND_DIR%\ragctl.js" %*
