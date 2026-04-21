@echo off
chcp 65001 >nul
title Bilibili Hot100 Launcher
color 0A

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set FRONTEND_PORT=3000
set BACKEND_PORT=8000
set DATA_DIR=%SCRIPT_DIR%data

:: Parse arguments
set MODE=all
if "%~1"=="--frontend-only" set MODE=frontend
if "%~1"=="--backend-only" set MODE=backend

echo ========================================
echo   Bilibili Hot100 Launcher
echo ========================================
echo.

echo [Mode] %MODE%
echo [Data Dir] %DATA_DIR%
echo.

:: =============================================
:: Discover Python
:: =============================================
echo [0/5] Discovering Python...
set PYTHON=

if defined PYTHON311 (
    if exist "%PYTHON311%\python.exe" set "PYTHON=%PYTHON311%\python.exe"
)

if not defined PYTHON (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        C:\Python311\python.exe
        C:\Python310\python.exe
    ) do (
        if not defined PYTHON (
            if exist %%~P set "PYTHON=%%~P"
        )
    )
)

if not defined PYTHON where python >nul 2>&1 set PYTHON=python

for /f "delims=" %%v in ('"%PYTHON%" --version 2^>^&1') do set "PYTHON_VER=%%v"
echo   Found: %PYTHON_VER%
echo.

:: =============================================
:: Kill processes on ports
:: =============================================
echo [1/5] Checking ports...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo   Backend port %BACKEND_PORT% occupied by PID %%a, terminating...
    taskkill /F /PID %%a >nul 2>&1
)
echo   Port %BACKEND_PORT% is free

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo   Frontend port %FRONTEND_PORT% occupied by PID %%a, terminating...
    taskkill /F /PID %%a >nul 2>&1
)
echo   Port %FRONTEND_PORT% is free
echo.

:: Create data directory
if not exist "%DATA_DIR%" (
    echo   Creating data directory: %DATA_DIR%
    mkdir "%DATA_DIR%"
)
echo.

:: =============================================
:: Backend
:: =============================================
if "%MODE%"=="frontend" goto :SKIP_BACKEND

echo [2/5] Starting backend service...

set BACKEND_DIR=%SCRIPT_DIR%bilibili-hot100-backend
set VENV_DIR=%BACKEND_DIR%.venv
set VENV_PY=%VENV_DIR%\Scripts\python.exe

:: Create or check venv
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import fastapi" >nul 2>&1
    if errorlevel 1 (
        echo   Recreating virtual environment...
        rmdir /s /q "%VENV_DIR%" 2>nul
        "%PYTHON%" -m venv "%VENV_DIR%"
        "%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    ) else (
        echo   Virtual environment OK.
    )
) else (
    echo   Creating virtual environment...
    "%PYTHON%" -m venv "%VENV_DIR%"
    "%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
)
echo   Dependencies ready.

echo   Starting backend on port %BACKEND_PORT%...
start "" cmd /c "cd /d "%BACKEND_DIR%" && "%VENV_PY%" -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
echo   Backend started.
echo.
goto :BACKEND_DONE

:SKIP_BACKEND
echo [2/5] Skipping backend.
echo.

:BACKEND_DONE

:: =============================================
:: Frontend
:: =============================================
if "%MODE%"=="backend" goto :SKIP_FRONTEND

echo [3/5] Starting frontend service...

set FRONTEND_DIR=%SCRIPT_DIR%bilibili-hot100-vue3-ts

if not exist "%FRONTEND_DIR%\node_modules" (
    echo   Installing frontend dependencies...
    pushd "%FRONTEND_DIR%"
    call npm install
    popd
    echo   Dependencies installed.
)

echo   Starting frontend on port %FRONTEND_PORT%...
start "" cmd /c "cd /d "%FRONTEND_DIR%" && npm run dev -- --port %FRONTEND_PORT%"
echo   Frontend started.
echo.
goto :FRONTEND_DONE

:SKIP_FRONTEND
echo [3/5] Skipping frontend.
echo.

:FRONTEND_DONE

:: Wait for services to be ready
echo [4/5] Waiting for services...
timeout /t 5 /nobreak >nul
echo.

:: =============================================
:: Done
:: =============================================
echo [5/5] Done.
echo.
echo ========================================
echo   All services started!
echo ========================================
echo.
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo.
echo   Use stop-all.bat to stop services.
echo.

:: Open browser
start http://localhost:%FRONTEND_PORT%

echo   Press Ctrl+C to stop all services
echo.
endlocal
