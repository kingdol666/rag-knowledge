@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  RAG Knowledge Platform - Unified Launcher
REM  Usage: start.bat [dev|prod]
REM    Each service starts in its own terminal window.
REM ============================================

set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"
if /i "%MODE%"=="d" set "MODE=dev"
if /i "%MODE%"=="p" set "MODE=prod"

echo.
echo  ============================================
echo   RAG Knowledge Platform - Mode: %MODE%
echo  ============================================
echo.

REM ---- Resolve root ----
set "ROOT=%~dp0"
set "ENV_FILE=%ROOT%.env"

if not exist "%ENV_FILE%" (
    echo  [ERROR] .env not found. Copy .env.example to .env
    exit /b 1
)

REM ---- Load .env for display ----
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "LINE=%%a"
    if not "!LINE:~0,1!"=="#" if not "%%a"=="" set "%%a=%%b"
)
if not defined BACKEND_PORT set "BACKEND_PORT=8001"
if not defined FRONTEND_PORT set "FRONTEND_PORT=3008"
if not defined WEB_PORT set "WEB_PORT=3009"

echo  [CONFIG] BACKEND_PORT=%BACKEND_PORT%
echo  [CONFIG] FRONTEND_PORT=%FRONTEND_PORT%
echo  [CONFIG] WEB_PORT=%WEB_PORT%
echo.

REM ---- Check submodules ----
if not exist "%ROOT%backend\app" (
    echo  [ERROR] Backend not found. Run: git submodule update --init --recursive
    exit /b 1
)
if not exist "%ROOT%frontend\package.json" (
    echo  [ERROR] Frontend not found. Run: git submodule update --init --recursive
    exit /b 1
)
if not exist "%ROOT%web\package.json" (
    echo  [ERROR] Web not found. Run: git submodule update --init --recursive
    exit /b 1
)

REM ---- Install deps if needed ----
if not exist "%ROOT%frontend\node_modules" (
    echo  [INFO] Installing frontend deps...
    cd /d "%ROOT%frontend" && npm install && cd /d "%ROOT%"
)
if not exist "%ROOT%web\node_modules" (
    echo  [INFO] Installing web deps...
    cd /d "%ROOT%web" && npm install && cd /d "%ROOT%"
)
echo.

REM ============================================================
REM  Launch each service in its own terminal window
REM ============================================================

echo  [1/3] Starting Backend...
start "RAG-Backend (port %BACKEND_PORT%)" "%ROOT%scripts\start-backend.bat"

echo  [2/3] Starting Frontend...
start "RAG-Frontend (port %FRONTEND_PORT%)" "%ROOT%scripts\start-frontend.bat"

echo  [3/3] Starting Web...
start "RAG-Web (port %WEB_PORT%)" "%ROOT%scripts\start-web.bat"

echo.
echo  ============================================
echo  [READY] 3 terminals launched!
echo.
echo    Backend (API):   http://localhost:%BACKEND_PORT%
echo    API Docs:        http://localhost:%BACKEND_PORT%/docs
echo    Frontend (Vue):  http://localhost:%FRONTEND_PORT%
echo    Web (Nuxt):      http://localhost:%WEB_PORT%
echo.
echo    Close each terminal to stop its service.
echo  ============================================
echo.
