@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================
REM  RAG Knowledge Platform - Unified Launcher (Windows)
REM  Usage: start.bat [dev|prod]
REM    Launches Backend + Web (Nuxt 3) in separate terminals.
REM    Ports read from config.yml (single source of truth).
REM ============================================================

set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"
if /i "%MODE%"=="d" set "MODE=dev"
if /i "%MODE%"=="p" set "MODE=prod"

echo.
echo   💡 Tip: Use 'ragctl setup' for first-time one-click deployment
echo   💡 Tip: Use 'ragctl up' to start all services
echo   💡 Tip: Use 'ragctl check' to audit your environment
echo.
echo  ==================================================
echo    RAG Knowledge Platform - Mode: %MODE%
echo  ==================================================
echo.

REM Check Node.js
where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Node.js not found. Install from https://nodejs.org/
    exit /b 1
)

REM Delegate to ragctl up
node "%ROOT%\command\ragctl.js" up --mode %MODE% 2>&1
if errorlevel 1 (
    echo.
    echo   [WARN] ragctl up failed — trying fallback direct launch...
    echo.
    goto :fallback
)
goto :eof

:fallback
REM ── Fallback: direct launch (only if ragctl up failed) ──
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where uv >nul 2>&1
if errorlevel 1 ( echo [ERROR] uv not found; exit /b 1 )

where npm >nul 2>&1
if errorlevel 1 ( echo [ERROR] npm not found; exit /b 1 )

if not exist "%ROOT%\web\node_modules" (
    echo   [INFO] Installing web deps...
    pushd "%ROOT%\web" && call npm install && popd
)

echo   Starting Backend (dev terminal)...
start "RAG-Backend (%MODE%)" cmd /c "cd /d "%ROOT%\backend" && uv run python main.py"
echo   Starting Web (dev terminal)...
start "RAG-Web (%MODE%)" cmd /c "cd /d "%ROOT%\web" && node start.mjs"

echo.
echo  ==================================================
echo   [READY] Backend + Web launched in new terminals.
echo   Close each terminal to stop its service.
echo  ==================================================
echo.
