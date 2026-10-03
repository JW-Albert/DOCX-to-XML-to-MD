#!/bin/bash

set -e

[ -t 1 ] && clear 2>/dev/null || true

PYTHON_VERSION="3.10"
VENV_DIR="venv"

echo "[INFO] Build Virtual Python${PYTHON_VERSION} Env."
uv venv --python "${PYTHON_VERSION}" "${VENV_DIR}"
echo "[INFO] Venv Build Completed"

echo "[INFO] Install Python3 Required Package"
uv pip install --python "${VENV_DIR}/bin/python" -e ".[dev]"

# echo "[INFO] Install PyTorch with CUDA"
# uv pip install --python "${VENV_DIR}/bin/python" torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo "[INFO] Install Completed"
