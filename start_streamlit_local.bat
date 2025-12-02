@echo off
REM Wrapper to run the PowerShell helper script with ExecutionPolicy Bypass
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_streamlit_local.ps1"
EXIT /B %ERRORLEVEL%
