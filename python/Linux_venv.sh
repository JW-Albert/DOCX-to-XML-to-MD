#!/bin/bash

set -e

[ -t 1 ] && clear 2>/dev/null || true

echo "[INFO] Build Virtual Python3 Env."
python3 -m venv venv
echo "[INFO] Venv Build Completed"

echo "[INFO] Upgrade PIP Version."
venv/bin/pip install --upgrade pip

echo "[INFO] Install Python3 Required Package"
venv/bin/pip install -e ".[dev]"

# echo "[INFO] Install PyTorch with CUDA"
# venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

echo "[INFO] Install Completed"