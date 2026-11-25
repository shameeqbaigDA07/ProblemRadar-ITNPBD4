@echo off
title Problem Radar - setup
cd /d "%~dp0"
echo ============================================
echo   Problem Radar - one-time setup
echo ============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python was not found on this computer.
  echo Install Python 3 from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during installation.
  echo Then double-click setup.bat again.
  pause
  exit /b 1
)
%PY% --version

if not exist ".venv\Scripts\python.exe" (
  echo Creating a private Python environment for this project...
  %PY% -m venv .venv
)

echo.
echo Installing the libraries. This can take a few minutes...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Installing failed. Copy the messages above and send them to Claude.
  pause
  exit /b 1
)

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created your .env file.
)

echo.
echo ============================================
echo   Setup finished.
echo   Notepad will now open your .env file.
echo   Paste your Gemini and Tavily keys after the = signs,
echo   then press Ctrl+S to save and close Notepad.
echo ============================================
notepad ".env"
echo.
echo Next: double-click run_tests.bat, then start_app.bat
pause
