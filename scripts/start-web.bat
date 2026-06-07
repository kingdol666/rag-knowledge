@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM ============================================
REM  RAG Knowledge - Web (Nuxt 3) Launcher
REM ============================================

set "ROOT=%~dp0.."
set "WEB_DIR=%ROOT%\web"
set "ENV_FILE=%ROOT%\.env"

REM Load .env
for /f "usebackq tokens=1,* delims==" %%a in ("%ENV_FILE%") do (
    set "LINE=%%a"
    if not "!LINE:~0,1!"=="#" if not "%%a"=="" set "%%a=%%b"
)
if not defined WEB_PORT set "WEB_PORT=3009"
if not defined PDF_PARSER_API_URL set "PDF_PARSER_API_URL=http://localhost:%BACKEND_PORT%"
if not defined DEEPAGENT_API_URL set "DEEPAGENT_API_URL=http://localhost:%BACKEND_PORT%"

echo.
echo  [Web]  http://localhost:%WEB_PORT%
echo  [API]  %PDF_PARSER_API_URL%
echo.

cd /d "%WEB_DIR%"
set NUXT_PUBLIC_API_BASE=%NUXT_PUBLIC_API_BASE%
set PDF_PARSER_API_URL=%PDF_PARSER_API_URL%
set DEEPAGENT_API_URL=%DEEPAGENT_API_URL%
npx nuxt dev --host 0.0.0.0 --port %WEB_PORT%
pause
