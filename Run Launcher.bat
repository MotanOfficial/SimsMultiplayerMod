@echo off
setlocal
set PYTHON=C:\Python314\python.exe
if not exist "%PYTHON%" (
    echo Python not found at %PYTHON% - edit Run Launcher.bat to set the correct path
    pause
    exit /b 1
)
"%PYTHON%" "%~dp0tools\launcher.py"
if errorlevel 1 pause
