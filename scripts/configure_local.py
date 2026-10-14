#!/usr/bin/env python3
"""Create private local development settings; never overwrite existing secrets."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved.")
else:
    text = (root / ".env.example").read_text()
    overrides = {"POSTGRES_USER": "pathable_owner", "APP_DB_USER": "pathable_app"}
    overrides.update(
        {
            k: os.environ.get(k) or secrets.token_urlsafe(32)
            for k in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "CSRF_SECRET", "RATE_LIMIT_HASH_KEY")
        }
    )
    lines = []
    for line in text.splitlines():
        key = line.split("=", 1)[0]
        lines.append(f"{key}={overrides.pop(key)}" if key in overrides else line)
    lines.extend(f"{k}={v}" for k, v in overrides.items())
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("\n".join(lines) + "\n")
    print("Private local development configuration created (values withheld).")
