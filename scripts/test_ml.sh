#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
.venv/bin/ruff check --config backend/pyproject.toml ml/pathable_ml ml/tests
.venv/bin/ruff format --config backend/pyproject.toml --check ml/pathable_ml ml/tests
export PYTHONPATH="$PWD/backend:$PWD"
.local/ml-venv/bin/python -m pytest -c backend/pyproject.toml ml/tests "$@"
