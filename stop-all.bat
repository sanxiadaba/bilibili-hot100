@echo off
chcp 65001 >nul
title Bilibili Hot100 Stopper
color 0C

echo ========================================
echo   Bilibili Hot100 Stopper
echo ========================================
echo.

set PID_DIR=%~dp0.pids

:: Check if PID files exist
if not exist "%PID_DIR%" (
    echo No PID directory found. Services may not be running.
    echo.
    echo Attempting to force kill by port...
    goto FORCE_KILL
)

:: Stop backend
echo [1/2] Stopping backend service...
if exist "%PID_DIR%\backend.pid" (
    set /p BACKEND_PID=<"%PID_DIR%\backend.pid"
    echo   Found backend PID: %BACKEND_PID%
    taskkill /F /PID %BACKEND_PID% >nul 2>&1
    if %errorlevel%==0 (
        echo   Backend stopped successfully
    ) else (
        echo   Backend process not found (already stopped?)
    )
    del "%PID_DIR%\backend.pid" >nul 2>&1
) else (
    echo   Backend PID file not found
)
echo.

:: Stop frontend
echo [2/2] Stopping frontend service...
if exist "%PID_DIR%\frontend.pid" (
    set /p FRONTEND_PID=<"%PID_DIR%\frontend.pid"
    echo   Found frontend PID: %FRONTEND_PID%
    taskkill /F /PID %FRONTEND_PID% >nul 2>&1
    if %errorlevel%==0 (
        echo   Frontend stopped successfully
    ) else (
        echo   Frontend process not found (already stopped?)
    )
    del "%PID_DIR%\frontend.pid" >nul 2>&1
) else (
    echo   Frontend PID file not found
)
echo.

:: Clean up PID directory
if exist "%PID_DIR%" (
    del /Q "%PID_DIR%\*.*" >nul 2>&1
    rmdir "%PID_DIR%" >nul 2>&1
    echo Cleaned up PID files
)

goto END

:FORCE_KILL
echo Force killing processes on ports 3000 and 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo   Killing process on port 3000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo   Killing process on port 8000 (PID: %%a)
    taskkill /F /PID %%a >nul 2>&1
)
echo.

:END
echo ========================================
echo   All services stopped
echo ========================================
echo.
pause
