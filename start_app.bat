@echo off
title Problem Radar - running
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please double-click setup.bat first.
  pause
  exit /b 1
)
echo Starting Problem Radar. Your browser will open in a moment.
echo Keep this window open while you use the app.
echo To stop the app, close this window.
echo.
".venv\Scripts\python.exe" app.py --open
pause
