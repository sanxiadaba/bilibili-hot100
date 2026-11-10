@echo off
rem Thin wrapper: every platform-specific step lives in launcher.py.
setlocal
set "PY=python"
where python >nul 2>&1 || set "PY=py"
where %PY% >nul 2>&1 || (
  echo Python 3.11+ is required but no Python launcher was found on PATH. 1>&2
  exit /b 1
)
"%PY%" "%~dp0launcher.py" --stop %*
exit /b %ERRORLEVEL%
