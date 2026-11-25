@echo off
title Problem Radar - Desktop shortcut
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'ProblemRadar.lnk')); $s.TargetPath='%~dp0'; $s.Save(); Write-Host ('Shortcut to this folder created on your Desktop: ' + $d)"
echo.
echo You can now open the project from the "ProblemRadar" icon on your Desktop.
pause
