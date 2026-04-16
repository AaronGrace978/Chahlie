@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel% equ 0 (
  python run.py %*
  exit /b %errorlevel%
)

where py >nul 2>&1
if %errorlevel% equ 0 (
  py run.py %*
  exit /b %errorlevel%
)

echo Python was not found. Install Python 3.10+ from python.org and ensure it is on PATH.
exit /b 1
