#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
task_artifact_root="$PWD/.local/release-build"
mkdir -p "$task_artifact_root/wheels" "$task_artifact_root/npm-project"
.venv/bin/python -m pip download --require-hashes --only-binary=:all: \
  --platform manylinux_2_28_x86_64 --platform manylinux_2_17_x86_64 \
  --platform manylinux2014_x86_64 --platform linux_x86_64 \
  --implementation cp --python-version 3.12 --abi cp312 --abi abi3 --abi none \
  -r backend/requirements.lock -d "$task_artifact_root/wheels"
cp frontend/package.json frontend/package-lock.json "$task_artifact_root/npm-project/"
npm ci --prefix "$task_artifact_root/npm-project" --cache "$task_artifact_root/npm-cache" \
  --ignore-scripts --os=linux --cpu=x64
