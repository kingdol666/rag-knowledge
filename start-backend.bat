@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  RAG Knowledge - Backend Launcher
REM ============================================

set "BACKEND_DIR=%~dp0backend"
set "ENV_FILE=%~dp0.env"

REM Load .env
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "LINE=%%a"
    if not "!LINE:~0,1!"=="#" if not "%%a"=="" set "%%a=%%b"
)
if not defined BACKEND_PORT set "BACKEND_PORT=8001"

echo.
echo  [Backend] http://localhost:%BACKEND_PORT%
echo  [Docs]    http://localhost:%BACKEND_PORT%/docs
echo.

cd /d "%BACKEND_DIR%"
set BACKEND_PORT=%BACKEND_PORT%
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload
pause
