@echo off
REM Double-click to start Job Alerts UI (no PowerShell typing)
cd /d "%~dp0"
set PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Python312\;%LOCALAPPDATA%\Programs\Python\Python312\Scripts\
start http://localhost:8000/
python main.py --mode api
pause
