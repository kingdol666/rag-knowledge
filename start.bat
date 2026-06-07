@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  RAG Knowledge Platform - Unified Launcher
REM  Usage: start.bat [dev|prod]
REM    dev  = Backend (uvicorn --reload) + Frontend (vite dev)   [default]
REM    prod = Backend (uvicorn) + Frontend (build if needed + vite preview)
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

REM ---- Load .env ----
set "ENV_FILE=%~dp0.env"
if not exist "%ENV_FILE%" (
    echo  [ERROR] .env file not found at %ENV_FILE%
    echo  [HINT]  Copy .env.example to .env and configure.
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "LINE=%%a"
    if not "!LINE:~0,1!"=="#" (
        if not "%%a"=="" set "%%a=%%b"
    )
)

REM Set defaults if not in .env
if not defined BACKEND_PORT set "BACKEND_PORT=8001"
if not defined FRONTEND_PORT set "FRONTEND_PORT=3000"
if not defined FRONTEND_PREVIEW_PORT set "FRONTEND_PREVIEW_PORT=4173"
if not defined VITE_API_BASE set "VITE_API_BASE=http://localhost:%BACKEND_PORT%"

echo  [CONFIG] BACKEND_PORT=%BACKEND_PORT%
echo  [CONFIG] FRONTEND_PORT=%FRONTEND_PORT%
echo  [CONFIG] VITE_API_BASE=%VITE_API_BASE%
echo.

REM ---- Resolve script directory (project root) ----
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "FRONTEND_DIR=%ROOT%frontend"

REM ---- Check prerequisites ----
where uv >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] uv not found. Install: https://docs.astral.sh/uv/
    exit /b 1
)

where node >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] node not found. Install Node.js 18+
    exit /b 1
)

if not exist "%BACKEND_DIR%\app" (
    echo  [ERROR] Backend directory not found: %BACKEND_DIR%
    echo  [HINT]  Run: git submodule update --init --recursive
    exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
    echo  [ERROR] Frontend directory not found: %FRONTEND_DIR%
    echo  [HINT]  Run: git submodule update --init --recursive
    exit /b 1
)

REM ---- Install frontend deps if needed ----
if not exist "%FRONTEND_DIR%\node_modules" (
    echo  [INFO] Installing frontend dependencies...
    cd /d "%FRONTEND_DIR%" && npm install && cd /d "%ROOT%"
    echo.
)

REM ---- Kill old processes on our ports ----
echo  [INFO] Cleaning old processes on ports %BACKEND_PORT%, %FRONTEND_PORT%, %FRONTEND_PREVIEW_PORT%...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%BACKEND_PORT% .*LISTENING"') do (
    taskkill /f /pid %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PORT% .*LISTENING"') do (
    taskkill /f /pid %%p >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PREVIEW_PORT% .*LISTENING"') do (
    taskkill /f /pid %%p >nul 2>&1
)
echo.

REM ---- Start Backend ----
echo  [BACKEND] Starting on http://localhost:%BACKEND_PORT%
echo  [BACKEND] API docs: http://localhost:%BACKEND_PORT%/docs
cd /d "%BACKEND_DIR%"
start /b "Backend" uv run python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload
cd /d "%ROOT%"
echo.

REM Wait for backend to be ready (max 20s)
echo  [INFO] Waiting for backend to start...
set BACKEND_READY=0
for /l %%i in (1,1,20) do (
    if !BACKEND_READY! equ 0 (
        curl -s http://localhost:%BACKEND_PORT%/api/v1/health >nul 2>&1
        if not errorlevel 1 (
            set BACKEND_READY=1
            echo  [BACKEND] Ready!
        ) else (
            timeout /t 1 /nobreak >nul
        )
    )
)
if !BACKEND_READY! equ 0 (
    echo  [WARN] Backend may still be starting...
)
echo.

REM ---- Start Frontend ----
cd /d "%FRONTEND_DIR%"
if /i "%MODE%"=="prod" (
    REM Prod mode: build if needed, then preview
    if not exist "dist\index.html" (
        echo  [FRONTEND] Building production bundle...
        set "VITE_API_BASE=%VITE_API_BASE%" && npm run build
        if errorlevel 1 (
            echo  [ERROR] Frontend build failed!
            cd /d "%ROOT%"
            exit /b 1
        )
        echo  [FRONTEND] Build complete!
        echo.
    ) else (
        echo  [FRONTEND] dist/ already exists, skipping build.
    )
    echo  [FRONTEND] Starting preview on http://localhost:%FRONTEND_PREVIEW_PORT%
    start /b "Frontend" npm run preview -- --port %FRONTEND_PREVIEW_PORT%
) else (
    REM Dev mode: vite dev server with HMR
    echo  [FRONTEND] Starting dev server on http://localhost:%FRONTEND_PORT%
    set "VITE_API_BASE=%VITE_API_BASE%" && start /b "Frontend" npm run dev -- --port %FRONTEND_PORT%
)
cd /d "%ROOT%"

echo.
echo  ============================================
echo  [READY] Services running!
if /i "%MODE%"=="prod" (
    echo    Frontend: http://localhost:%FRONTEND_PREVIEW_PORT%
) else (
    echo    Frontend: http://localhost:%FRONTEND_PORT%
)
echo    Backend:  http://localhost:%BACKEND_PORT%
echo    API Docs: http://localhost:%BACKEND_PORT%/docs
echo  ============================================
echo.
echo  Press Ctrl+C to stop all services...
echo.

REM Keep the script running
pause >nul
