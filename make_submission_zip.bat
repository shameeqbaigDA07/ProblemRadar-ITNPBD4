@echo off
REM Makes ProblemRadar_submission.zip on your Desktop.
REM Leaves out .env (your API keys), .venv, caches and old zips.
set "PROJECT=%~dp0."
cd /d "%PROJECT%"
set "STAGE=%TEMP%\ProblemRadar_submission"
if exist "%STAGE%" rmdir /s /q "%STAGE%"
robocopy "%PROJECT%" "%STAGE%\ProblemRadar" /E /XD .venv venv __pycache__ .pytest_cache .git /XF .env *.zip >nul
if exist "%STAGE%\ProblemRadar\.env" (
  echo ERROR: .env was copied. Stopping so your keys are not shared.
  pause
  exit /b 1
)
for /f "usebackq delims=" %%D in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESK=%%D"
if exist "%DESK%\ProblemRadar_submission.zip" del "%DESK%\ProblemRadar_submission.zip"
REM tar writes standard zip paths, so the zip opens correctly on Windows, Mac and Linux
tar -a -c -f "%DESK%\ProblemRadar_submission.zip" -C "%STAGE%" ProblemRadar
if errorlevel 1 (echo ERROR: the zip could not be made. & pause & exit /b 1)
rmdir /s /q "%STAGE%"
echo Done: %DESK%\ProblemRadar_submission.zip
echo.
echo Your keys (.env) are NOT in the zip. Open the zip to check before submitting.
pause
