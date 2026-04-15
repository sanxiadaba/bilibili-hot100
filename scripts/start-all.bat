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

:: Parse arguments
set MODE=all
if "%~1"=="--frontend-only" set MODE=frontend
if "%~1"=="--backend-only" set MODE=backend

echo [Mode] %MODE%
echo.

:: Clear backend port
echo [1/4] Checking backend port %BACKEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo   Found process PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    echo   Process terminated
)
echo   Port %BACKEND_PORT% is free
echo.

:: Clear frontend port
echo [2/4] Checking frontend port %FRONTEND_PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo   Found process PID: %%a
    taskkill /F /PID %%a >nul 2>&1
    echo   Process terminated
)
echo   Port %FRONTEND_PORT% is free
echo.

:: Start backend if needed
if "%MODE%"=="frontend" goto SKIP_BACKEND

echo [3/4] Starting backend service...
cd /d "%~dp0bilibili-hot100-backend"

:: Check virtual environment
if not exist ".venv" (
    echo   Creating virtual environment...
    python -m venv .venv
)

:: Install requirements if needed
if not exist ".venv\Lib\site-packages\fastapi" (
    echo   Installing backend dependencies...
    call .venv\Scripts\pip install -r requirements.txt
)

:: Start backend in background
start /B "Backend" cmd /c "cd /d "%~dp0bilibili-hot100-backend" && call .venv\Scripts\activate && python -m uvicorn main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
echo   Backend starting: http://localhost:%BACKEND_PORT%
echo.

:: Wait for backend to be ready
echo   Waiting for backend to be ready...
timeout /t 3 /nobreak >nul
echo   Backend should be ready now
echo.

:SKIP_BACKEND

:: Start frontend if needed
if "%MODE%"=="backend" goto SKIP_FRONTEND

echo [4/4] Starting frontend service...
cd /d "%~dp0bilibili-hot100-vue3-ts"

:: Check node_modules
if not exist "node_modules" (
    echo   Installing frontend dependencies...
    call npm install
)

echo.
echo ========================================
echo   All services started successfully!
echo ========================================
echo.
echo Access URLs:
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo.
echo Press Ctrl+C to stop all services
echo.

:: Open browser
echo Opening browser...
start http://localhost:%FRONTEND_PORT%

:: Start frontend (this will block)
npm run dev -- --port %FRONTEND_PORT%

:SKIP_FRONTEND

if "%MODE%"=="backend" (
    echo.
    echo Backend service is running on http://localhost:%BACKEND_PORT%
    echo Press Ctrl+C to stop
echo.
    pause
)

echo.
echo Services stopped.
pause
