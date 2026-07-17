@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================================
REM  RAG Knowledge Platform - Unified Launcher (Windows)
REM  Usage: start.bat [dev|prod]
REM    Silently launches Backend + Web (NO terminal windows).
REM    Ports read from config.yml (single source of truth).
REM    Logs → backend\logs\desktop-stdout.log + web\logs\desktop-stdout.log
REM    (same files the Tauri desktop console + `ragctl logs` read)
REM ============================================================

REM Resolve ROOT up-front (fixes the old "used-before-set" bug in fallback)
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"
if /i "%MODE%"=="d" set "MODE=dev"
if /i "%MODE%"=="p" set "MODE=prod"

echo.
echo   💡 Tip: Use 'ragctl setup' for first-time one-click deployment
echo   💡 Tip: Use 'ragctl up' to start all services (silent, no terminals)
echo   💡 Tip: Use 'ragctl logs [backend|web]' to view logs
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

REM Delegate to ragctl up (silent launcher — no terminal windows, dev AND prod)
node "%ROOT%\command\ragctl.js" up --mode %MODE% 2>&1
if not errorlevel 1 goto :eof

echo.
echo   [WARN] ragctl up failed — trying fallback silent launch...
echo.

:fallback
REM ── Fallback: SILENT direct launch (only if ragctl up failed) ──
REM No terminal windows open. Output goes to shared log files.

where uv >nul 2>&1
if errorlevel 1 ( echo [ERROR] uv not found; exit /b 1 )

where npm >nul 2>&1
if errorlevel 1 ( echo [ERROR] npm not found; exit /b 1 )

if not exist "%ROOT%\web\node_modules" (
    echo   [INFO] Installing web deps...
    pushd "%ROOT%\web" && call npm install && popd
)

REM Prepare log directories (shared with Tauri + ragctl)
if not exist "%ROOT%\backend\logs" mkdir "%ROOT%\backend\logs"
if not exist "%ROOT%\web\logs" mkdir "%ROOT%\web\logs"

REM cd to ROOT so relative paths in the child cmd have no spaces to quote.
cd /d "%ROOT%" 2>nul

REM start /b = no new window; stdout+stderr → shared log files (truncated).
REM Inner cwd is ROOT (inherited); after `cd backend`/`cd web`, `logs\...` resolves
REM to {ROOT}\backend\logs\... and {ROOT}\web\logs\... respectively. Inner command
REM has no embedded quotes so cmd /c parses it cleanly (handles spaces in ROOT).
echo   Starting Backend (silent^) ... log: backend\logs\desktop-stdout.log
start "" /b cmd /c "cd backend && set APP_MODE=%MODE% && set PYTHONUNBUFFERED=1 && uv run python main.py > logs\desktop-stdout.log 2>&1"

echo   Starting Web (silent^) ... log: web\logs\desktop-stdout.log
start "" /b cmd /c "cd web && set APP_MODE=%MODE% && set PYTHONUNBUFFERED=1 && node start.mjs > logs\desktop-stdout.log 2>&1"

echo.
echo  ==================================================
echo   [READY] Backend + Web launched silently (no terminals^).
echo   Logs:  ragctl logs backend  |  ragctl logs web
echo   Or open the Tauri desktop console.
echo  ==================================================
echo.
