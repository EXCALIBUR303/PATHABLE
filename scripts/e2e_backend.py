#!/usr/bin/env python3
"""Playwright-only backend with a fresh disposable database; never reset development data."""

import json
import os
import shutil
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def run():
    from app.cli import prepare_database
    from app.core.config import get_settings
    from app.models.entities import Profile, User
    from app.services.auth import hasher
    from app.services.seed import seed_demo

    original = get_settings()
    name = "pathable_e2e_" + uuid.uuid4().hex[:12]
    kwargs = original.database_url(
        owner=True, database="postgres"
    ).translate_connect_args(username="user", database="dbname")
    uploads = ROOT / ".local" / (name + "_uploads")
    os.environ["UPLOAD_ROOT"] = str(uploads)
    os.environ["POSTGRES_DB"] = name
    os.environ["APP_ORIGIN"] = "http://localhost:5174"
    get_settings.cache_clear()
    process = None
    settings = get_settings()
    test_engine = create_engine(settings.database_url(), hide_parameters=True)
    state = ROOT / ".local/e2e-state.json"
    try:
        prepare_database()
        with Session(test_engine) as db, db.begin():
            seed_demo(db)
            admin = User(
                normalized_email="browser-admin@example.com",
                display_name="Browser administrator",
                role="admin",
                password_hash=hasher.hash("test-only administrator password"),
            )
            db.add(admin)
            db.flush()
            db.add(Profile(user_id=admin.id))
        state.parent.mkdir(exist_ok=True)
        descriptor = os.open(state, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump({"database": name}, stream)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "18000",
                "--no-proxy-headers",
            ],
            cwd=ROOT / "backend",
        )

        def shutdown(_signal, _frame):
            if process and process.poll() is None:
                process.terminate()

        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        code = process.wait()
        if code not in (0, -15):
            raise SystemExit(code)
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        test_engine.dispose()
        assert name.startswith("pathable_e2e_") and name != original.postgres_db
        with psycopg.connect(**kwargs, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
        state.unlink(missing_ok=True)
        shutil.rmtree(uploads, ignore_errors=True)


if __name__ == "__main__":
    run()
