@echo off
chcp 65001 >nul 2>&1
set "SCRIPT_DIR=%~dp0"

:: Check if Node.js is available
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Node.js is not installed or not in PATH
    exit /b 1
)

:: Run the CLI
node "%SCRIPT_DIR%ragctl.js" %*