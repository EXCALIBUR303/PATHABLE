#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
.venv/bin/ruff check --config backend/pyproject.toml \
  scripts/configure_release.py scripts/release_support.py scripts/release.py \
  scripts/backup_release.py scripts/smoke_release.py scripts/verify_release_restore.py \
  scripts/verify_release_clean.py scripts/smoke_release_browser.py
.venv/bin/pytest scripts/tests -q
.venv/bin/ruff format --check --config backend/pyproject.toml \
  scripts/configure_release.py scripts/release_support.py scripts/release.py \
  scripts/backup_release.py scripts/smoke_release.py scripts/verify_release_restore.py \
  scripts/verify_release_clean.py scripts/smoke_release_browser.py
bash scripts/prepare_release_artifacts.sh
task_fixture_id="$(.venv/bin/python -c 'import uuid; print(uuid.uuid4().hex[:10])')"
task_fixture_root="$PWD/.local/release-test-$task_fixture_id"
task_fixture_port="$(.venv/bin/python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
.venv/bin/python scripts/configure_release.py --local-test --directory "$task_fixture_root" \
  --project "pathable-release-test-$task_fixture_id" --port "$task_fixture_port"
trap '.venv/bin/python scripts/release.py --env "$task_fixture_root/config.env" stop --all' EXIT
.venv/bin/python scripts/release.py --env "$task_fixture_root/config.env" build --discard-build-cache
.venv/bin/python scripts/release.py --env "$task_fixture_root/config.env" init --synthetic
.venv/bin/python scripts/release.py --env "$task_fixture_root/config.env" start
.venv/bin/python scripts/smoke_release.py --env "$task_fixture_root/config.env"
.venv/bin/python scripts/smoke_release_browser.py --env "$task_fixture_root/config.env"
.venv/bin/python scripts/verify_release_restore.py --env "$task_fixture_root/config.env"
.venv/bin/python scripts/verify_release_clean.py
