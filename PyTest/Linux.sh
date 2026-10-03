#! /bin/bash

set -e

safe_clear() {
    if [ -t 1 ] && [ -n "$TERM" ] && command -v clear >/dev/null 2>&1; then
        clear 2>/dev/null || true
    fi
}

cleanup() {
    deactivate 2>/dev/null || true
}
trap cleanup EXIT

safe_clear

source venv/bin/activate

safe_clear

pytest tests
