@echo off
title Problem Radar - key check
cd /d "%~dp0"
.venv\Scripts\python check_keys.py
pause
