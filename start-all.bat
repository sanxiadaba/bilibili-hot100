@echo off
chcp 65001 >nul
title Bilibili Hot100 Launcher
color 0A

echo ========================================
echo   Bilibili Hot100 Launcher
echo ========================================
echo.

set FRONTEND_PORT=3000
set BACKEND_PORT=8000

:: Default data directory (can be customized)
if "%DATA_DIR%"=="" set DATA_DIR=%~dp0data

:: Parse arguments
set MODE=all
set DETACHED=false
if "%~1"=="--frontend-only" set MODE=frontend
if "%~1"=="--backend-only" set MODE=backend
if "%~1"=="--detached" set DETACHED=true
if "%~1"=="--data-dir" (
    set DATA_DIR=%~2
    shift
    shift
)

echo [Mode] %MODE%
echo [Detached] %DETACHED%
echo [Data Dir] %DATA_DIR%
echo.

:: =============================================
:: Dynamically discover Python executable
:: =============================================
echo [0/5] Discovering Python...
set PYTHON=
set PYTHON_VER=

:: Check environment variable first
if not "%PYTHON311%"=="" (
    if exist "%PYTHON311%\python.exe" (
        set "PYTHON=%PYTHON311%\python.exe"
    )
)

:: Search common installation paths
if "%PYTHON%"=="" (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        C:\Python311\python.exe
        C:\Python310\python.exe
        C:\Python39\python.exe
        C:\Python312\python.exe
    ) do (
        if exist "%%~P" (
            set "PYTHON=%%~P"
        )
    )
)

:: Fallback to PATH
if "%PYTHON%"=="" where python >nul 2>&1 set PYTHON=python

if "%PYTHON%"=="" (
    echo   ERROR: Python not found. Please install Python 3.8+
    echo   Download: https://python.org
    exit /b 1
)

for /f "delims=" %%v in ('"%PYTHON%" --version 2^>^&1') do set "PYTHON_VER=%%v"
echo   Found: %PYTHON_VER% ^(%PYTHON%^)
echo.

:: Clear backend port
echo [1/5] Checking backend port %BACKEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo   Found process PID: %%a, terminating...
    taskkill /F /PID %%a >nul 2>&1
    echo   Process terminated
)
echo   Port %BACKEND_PORT% is free
echo.

:: Clear frontend port
echo [2/5] Checking frontend port %FRONTEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo   Found process PID: %%a, terminating...
    taskkill /F /PID %%a >nul 2>&1
    echo   Process terminated
)
echo   Port %FRONTEND_PORT% is free
echo.

:: Create PID directory
if not exist "%~dp0.pids" mkdir "%~dp0.pids"

:: Start backend if needed
if "%MODE%"=="frontend" goto SKIP_BACKEND

echo [3/5] Starting backend service...
cd /d "%~dp0bilibili-hot100-backend"

:: Create data directory if not exists
if not exist "%DATA_DIR%" (
    echo   Creating data directory: %DATA_DIR%
    mkdir "%DATA_DIR%"
)

:: Check if venv exists and is working (fastapi installed)
if exist ".venv\Scripts\python.exe" (
    if exist ".venv\Lib\site-packages\fastapi" (
        echo   Virtual environment already exists and fastapi is installed, skipping venv creation.
        call .venv\Scripts\pip install --upgrade pip >nul 2>&1
        call .venv\Scripts\pip install -r requirements.txt >nul 2>&1
    ) else (
        echo   Recreating virtual environment (fastapi not found in existing venv)...
        rmdir /s /q .venv >nul 2>&1
        "%PYTHON%" -m venv .venv
        call .venv\Scripts\pip install --upgrade pip >nul 2>&1
        call .venv\Scripts\pip install -r requirements.txt >nul 2>&1
    )
) else (
    echo   Creating virtual environment...
    "%PYTHON%" -m venv .venv
    call .venv\Scripts\pip install --upgrade pip >nul 2>&1
    call .venv\Scripts\pip install -r requirements.txt >nul 2>&1
)
echo   Dependencies installed
echo.

:: Start backend in background
echo   Starting backend process...
set BACKEND_LOG=%~dp0.pids\backend.log
start /B "Backend" cmd /c "cd /d "%~dp0bilibili-hot100-backend" && .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload > "%BACKEND_LOG%" 2>&1"

:: Wait for startup
timeout /t 4 /nobreak >nul

:: Save PID by matching the uvicorn process
set BACKEND_PID_FILE=%~dp0.pids\backend.pid
for /f "tokens=2" %%a in ('wmic process where "name='python.exe' and commandline like '%%uvicorn%%'" get processid 2^>nul') do echo %%a > "%BACKEND_PID_FILE%"
echo   Backend started: http://localhost:%BACKEND_PORT%
echo   PID saved to: %BACKEND_PID_FILE%
echo.

:SKIP_BACKEND

:: Start frontend if needed
if "%MODE%"=="backend" goto SKIP_FRONTEND

echo [4/5] Starting frontend service...
cd /d "%~dp0bilibili-hot100-vue3-ts"

:: Check node_modules
if not exist "node_modules" (
    echo   Installing frontend dependencies...
    call npm install >nul 2>&1
    echo   Dependencies installed
)

:: Start frontend dev server
echo   Starting frontend dev server...
set FRONTEND_PID_FILE=%~dp0.pids\frontend.pid
set FRONTEND_LOG=%~dp0.pids\frontend.log
start /B "Frontend" cmd /c "cd /d "%~dp0bilibili-hot100-vue3-ts" && npm run dev -- --port %FRONTEND_PORT% > "%FRONTEND_LOG%" 2>&1"

:: Wait for startup
timeout /t 4 /nobreak >nul

:: Save PID by matching the vite/node process
for /f "tokens=2" %%a in ('wmic process where "name='node.exe' and commandline like '%%vite%%'" get processid 2^>nul') do echo %%a > "%FRONTEND_PID_FILE%"
echo   Frontend started: http://localhost:%FRONTEND_PORT%
echo   PID saved to: %FRONTEND_PID_FILE%
echo.

:SKIP_FRONTEND

echo [5/5] Finalizing...
echo.
echo ========================================
echo   All services started successfully!
echo ========================================
echo.
echo Access URLs:
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo   Python:   %PYTHON_VER%
echo   Data Dir: %DATA_DIR%
echo.
echo Process files:
echo   Backend PID: %~dp0.pids\backend.pid
echo   Frontend PID: %~dp0.pids\frontend.pid
echo.

:: Save service info
(
echo Frontend: http://localhost:%FRONTEND_PORT%
echo Backend: http://localhost:%BACKEND_PORT%
echo API Docs: http://localhost:%BACKEND_PORT%/docs
) > "%~dp0.pids\services.txt"

:: Open browser
echo Opening browser...
start http://localhost:%FRONTEND_PORT%

if "%DETACHED%"=="true" (
    echo.
    echo Services running in background.
    echo Use stop-all.bat to stop services.
    echo.
    exit /b 0
)

echo.
echo Press Ctrl+C to stop all services
echo.

:: Keep script running to maintain foreground process
:WAIT_LOOP
timeout /t 5 /nobreak >nul
goto WAIT_LOOP
