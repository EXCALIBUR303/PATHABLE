#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export DOCKER_CONFIG="$PWD/.local/docker"
mkdir -p "$DOCKER_CONFIG"
docker compose up -d --wait db
(cd backend && ../.venv/bin/python -m app.cli prepare-db && ../.venv/bin/python -m app.cli seed --synthetic --if-empty && ../.venv/bin/python -m app.cli maintenance)
.venv/bin/python scripts/dev.py start
.venv/bin/python scripts/smoke_api.py
.venv/bin/python scripts/smoke_routes.py
.venv/bin/python scripts/smoke_events.py
.venv/bin/python scripts/smoke_ml.py
.venv/bin/python scripts/web.py start
.venv/bin/python scripts/smoke_frontend.py
