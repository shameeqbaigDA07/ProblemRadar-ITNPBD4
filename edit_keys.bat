@echo off
title Problem Radar - API keys
cd /d "%~dp0"
if not exist ".env" copy ".env.example" ".env" >nul
echo Notepad is opening your .env file.
echo 1. Paste your Gemini key straight after GEMINI_API_KEY=
echo 2. Paste your Tavily key straight after TAVILY_API_KEY=
echo    Backup: add a new line GROQ_API_KEY=your-groq-key
echo    (free at console.groq.com/keys) so the app can switch
echo    to Groq when Gemini is busy.
echo 3. Press Ctrl+S to save, then close Notepad.
echo 4. Close the start_app window and double-click start_app.bat again.
notepad ".env"
