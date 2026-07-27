@echo off
setlocal
set "MODE=all"
if /I "%~1"=="--frontend-only" set "MODE=frontend"
if /I "%~1"=="--backend-only" set "MODE=backend"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\service-manager.ps1" -Action Stop -Mode "%MODE%"
exit /b %ERRORLEVEL%
