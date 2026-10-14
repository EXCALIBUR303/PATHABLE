#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../backend"
../.venv/bin/ruff check app alembic
../.venv/bin/ruff format --check app alembic
../.venv/bin/pytest "$@"
