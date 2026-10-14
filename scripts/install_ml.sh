#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -c 'import sys,platform; assert sys.version_info[:2] == (3,12) and platform.system()=="Linux" and platform.machine()=="x86_64", "Optional locked ML runtime currently supports Linux x86_64/Python 3.12"'
python3 -m venv .local/ml-venv
export PIP_CACHE_DIR="$PWD/.local/pip-cache"
.local/ml-venv/bin/python -m pip install --require-hashes -r backend/requirements.lock -r ml/requirements.lock
.local/ml-venv/bin/python -m pip check
python3 scripts/configure_ml.py
(cd backend && ../.venv/bin/python -m app.cli prepare-db)
