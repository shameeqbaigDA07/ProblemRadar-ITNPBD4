@echo off
title Problem Radar - tests
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please double-click setup.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pytest
echo.
echo The last line above shows how many tests passed or failed.
echo Take a screenshot of it for your development log.
pause
