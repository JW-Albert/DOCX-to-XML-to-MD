@echo off

set VENV_DIR=venv

echo [INFO] Run PyTest
"%VENV_DIR%\Scripts\python.exe" -m pytest tests
set EXIT_CODE=%ERRORLEVEL%

exit /b %EXIT_CODE%
