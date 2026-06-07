@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  RAG Knowledge - Frontend (Vue+Vite) Launcher
REM ============================================

set "ROOT=%~dp0.."
set "FRONTEND_DIR=%ROOT%\frontend"
set "ENV_FILE=%ROOT%\.env"

REM Load .env
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "LINE=%%a"
    if not "!LINE:~0,1!"=="#" if not "%%a"=="" set "%%a=%%b"
)
if not defined FRONTEND_PORT set "FRONTEND_PORT=3008"
if not defined VITE_API_BASE set "VITE_API_BASE=http://localhost:%BACKEND_PORT%"

echo.
echo  [Frontend] http://localhost:%FRONTEND_PORT%
echo  [Proxy]    /api -^> %VITE_API_BASE%
echo.

cd /d "%FRONTEND_DIR%"
set VITE_API_BASE=%VITE_API_BASE%
npm run dev -- --port %FRONTEND_PORT%
pause
