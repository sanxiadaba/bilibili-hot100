@echo off
setlocal
set "MODE=all"
set "DETACHED="
set "DATA_DIR=%~dp0data"

:parse
if "%~1"=="" goto run
if /I "%~1"=="--frontend-only" (
  set "MODE=frontend"
  shift
  goto parse
)
if /I "%~1"=="--backend-only" (
  set "MODE=backend"
  shift
  goto parse
)
if /I "%~1"=="--detached" (
  set "DETACHED=-Detached"
  shift
  goto parse
)
if /I "%~1"=="--data-dir" (
  if "%~2"=="" echo Missing value for --data-dir.& exit /b 2
  set "DATA_DIR=%~2"
  shift
  shift
  goto parse
)
echo Unknown argument: %~1
exit /b 2

:run
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\service-manager.ps1" -Action Start -Mode "%MODE%" -DataDir "%DATA_DIR%" %DETACHED%
exit /b %ERRORLEVEL%
