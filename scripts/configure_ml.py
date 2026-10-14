#!/usr/bin/env python3
"""Add one local restricted-worker credential without enabling ML or printing secrets."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if not path.is_file():
    raise SystemExit("Run the core installation first")
text = path.read_text()
if not os.environ.get("ML_WORKER_DB_PASSWORD") and not any(
    line.startswith("ML_WORKER_DB_PASSWORD=") for line in text.splitlines()
):
    with path.open("a") as stream:
        stream.write("\nML_WORKER_DB_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
    path.chmod(0o600)
print("Local ML worker binding preserved or created; inference remains disabled")
