@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 启动前端：cd web → 设 APP_MODE → npm run dev|start
set "MODE=%~1"
if "%MODE%"=="" set "MODE=dev"
if /i "%MODE%"=="d" set "MODE=dev"
if /i "%MODE%"=="p" set "MODE=prod"

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%\..") do set "ROOT=%%~fi"

set "APP_MODE=%MODE%"
cd /d "%ROOT%\web"

echo [start-web] mode=%MODE%  dir=%ROOT%\web
if /i "%MODE%"=="prod" (
    call npm run start
) else (
    call npm run dev
)
