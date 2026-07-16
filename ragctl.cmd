@echo off
chcp 65001 >nul 2>&1

REM ============================================================
REM  ragctl.cmd — RAG Knowledge Platform CLI (Windows cmd)
REM ============================================================
REM Same as ragctl.bat — provides .cmd extension for cmd.exe compatibility
REM ============================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "COMMAND_DIR=%ROOT%\command"

if not exist "%COMMAND_DIR%\node_modules" (
    echo   [setup] Installing ragctl dependencies...
    cd /d "%COMMAND_DIR%"
    call npm install --silent >nul 2>&1
)

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js not found. Install from https://nodejs.org/
    exit /b 1
)

node "%COMMAND_DIR%\ragctl.js" %*
