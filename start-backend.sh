#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
