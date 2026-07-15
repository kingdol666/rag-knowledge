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

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

echo.
echo   💡 Tip: Use 'ragctl init' for first-time setup, then 'ragctl up' to start.
echo   💡 Tip: Use 'ragctl doctor' to diagnose any issues.
echo.
echo  ==================================================
echo    RAG Knowledge Platform - Mode: %MODE%
echo  ==================================================
echo.

REM ── Prerequisite checks ─────────────────────────────────
where uv >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] 'uv' not found. Install: https://docs.astral.sh/uv/
    exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] 'node' not found. Install Node.js 18+.
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] 'npm' not found. Install Node.js 18+.
    exit /b 1
)

REM ── Submodule check ─────────────────────────────────────
if not exist "%ROOT%\backend\app" (
    echo   [ERROR] Backend submodule not found.
    echo   Run: git submodule update --init --recursive
    exit /b 1
)
if not exist "%ROOT%\web\package.json" (
    echo   [ERROR] Web submodule not found.
    echo   Run: git submodule update --init --recursive
    exit /b 1
)

REM ── Install web deps if needed ──────────────────────────
if not exist "%ROOT%\web\node_modules" (
    echo   [INFO] Installing web deps...
    pushd "%ROOT%\web"
    call npm install
    popd
)

REM ── Optional: Neo4j status (informational) ──────────────
where docker >nul 2>&1
if not errorlevel 1 (
    docker ps --format "{{.Names}}" 2>nul | findstr /C:"rag-knowledge-neo4j" >nul 2>&1
    if not errorlevel 1 (
        echo   [INFO] Neo4j container detected ^(graph features available^)
    ) else (
        echo   [INFO] Neo4j container not running - graph features will be degraded
        echo          Start it with: docker compose up -d neo4j
    )
)
echo.

REM ── Launch services ─────────────────────────────────────
echo   [1/2] Starting Backend...
start "RAG-Backend (%MODE%)" "%ROOT%\scripts\start-backend.bat" %MODE%

echo   [2/2] Starting Web...
start "RAG-Web (%MODE%)" "%ROOT%\scripts\start-web.bat" %MODE%

echo.
echo  ==================================================
echo   [READY] 2 terminals launched!
echo.
echo     Backend (API):  port from config.yml [mode=%MODE%]
echo     Web (Nuxt):     port from config.yml [mode=%MODE%]
echo.
echo     Close each terminal to stop its service.
echo  ==================================================
echo.
