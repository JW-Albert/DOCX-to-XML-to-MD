@echo off

set VENV_DIR=venv
set PYTHON_VERSION=3.10.19

echo [INFO] Remove Virtual Python%PYTHON_VERSION% Environment.
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%"

echo [INFO] Build Virtual Python%PYTHON_VERSION% Environment.
uv venv --python "%PYTHON_VERSION%" --seed "%VENV_DIR%"
echo [INFO] Venv Build Completed

echo [INFO] Upgrade PIP Version.
uv pip install --python "%VENV_DIR%\Scripts\python.exe" --upgrade pip

echo [INFO] Install Python3 Required Package
uv pip install --python "%VENV_DIR%\Scripts\python.exe" -e ".[dev]"

@REM echo [INFO] Install PyTorch in Virtual Python%PYTHON_VERSION% Environment.
@REM "%VENV_DIR%\Scripts\pip.exe" install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo [INFO] Install Completed