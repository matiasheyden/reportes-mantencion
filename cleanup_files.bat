@echo off
REM Cleanup script to remove temporary/backups/logs and sample PDFs
cd /d "%~dp0"
echo Removing backup and log files...
del /f /q "app.py.bak" 2>nul
del /f /q "reporte.py.bak" 2>nul
del /f /q "streamlit_run.log" 2>nul
del /f /q "streamlit_run.log.bak" 2>nul
del /f /q "reportlab-userguide.pdf" 2>nul
del /f /q "test_pdf.py" 2>nul
del /f /q "bitacora_15-10.pdf" 2>nul
del /f /q "bitacora_15-10_styled.pdf" 2>nul
del /f /q "bitacora_22-10.pdf" 2>nul
del /f /q "bitacora_22-10_styled.pdf" 2>nul
echo Cleanup finished.
pause
