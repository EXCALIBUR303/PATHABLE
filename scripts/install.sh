#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 scripts/configure_local.py
python3 -m venv .venv
export PIP_CACHE_DIR="$PWD/.local/pip-cache"
export DOCKER_CONFIG="$PWD/.local/docker"
mkdir -p "$PIP_CACHE_DIR" "$DOCKER_CONFIG"
.venv/bin/python -m pip install --require-hashes -r backend/requirements.lock
docker compose up -d --wait db
cd backend
../.venv/bin/python -m app.cli prepare-db
../.venv/bin/python -m app.cli seed --synthetic --if-empty
cd ../frontend
node -e 'if (Number(process.versions.node.split(".")[0]) !== 24) throw new Error("PathAble frontend requires Node 24")'
npm ci
