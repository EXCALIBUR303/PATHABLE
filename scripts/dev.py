#!/usr/bin/env python3
"""Start/stop only the API process recorded by this checkout, with identity checks."""

import argparse
import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
LOCAL = ROOT / ".local"
STATE = LOCAL / "api-process.json"
PORT = int(os.environ.get("API_PORT", "8000"))


def identity(pid):
    try:
        os.kill(pid, 0)
        status = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="], capture_output=True, text=True, check=True
        )
        if status.stdout.strip().startswith("Z"):
            return None
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "args="],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (ProcessLookupError, PermissionError, subprocess.CalledProcessError):
        return None


def owned():
    if not STATE.exists():
        return None
    state = json.loads(STATE.read_text())
    current = identity(state["pid"])
    if current and current == state["identity"] and "uvicorn app.main:app" in current:
        return state
    if current:
        raise SystemExit("Recorded PID belongs to another process; refusing to stop or replace it")
    return None


def ready():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/v1/health/ready", timeout=2) as r:
            return json.load(r) == {"status": "ready"}
    except (OSError, ValueError, urllib.error.URLError):
        return False


def start():
    existing = owned()
    if existing:
        if ready():
            print("Existing PathAble API is ready")
            return
        raise SystemExit("Existing API is not ready; inspect .local/api.log before restarting")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", PORT))
        except OSError:
            raise SystemExit(
                f"Port {PORT} is already in use; no unrelated process was stopped"
            ) from None
    LOCAL.mkdir(exist_ok=True)
    descriptor = os.open(LOCAL / "api.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "a") as log:
        process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(PORT),
                "--no-proxy-headers",
            ],
            cwd=ROOT / "backend",
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    # Wait for exec to settle before recording command identity for future stops.
    recorded = False
    for _ in range(100):
        if process.poll() is not None:
            raise SystemExit("API startup failed; inspect .local/api.log")
        if not recorded:
            current = identity(process.pid)
            if current and "uvicorn app.main:app" in current:
                STATE.write_text(
                    json.dumps({"pid": process.pid, "identity": current, "port": PORT}) + "\n"
                )
                recorded = True
        if recorded and ready():
            print("PathAble API started and database readiness passed")
            return
        time.sleep(0.2)
    raise SystemExit("API readiness timed out; inspect .local/api.log")


def stop():
    state = owned()
    if not state:
        print("No running API process owned by this checkout")
        return
    os.kill(state["pid"], signal.SIGTERM)
    for _ in range(50):
        if not identity(state["pid"]):
            break
        time.sleep(0.1)
    else:
        raise SystemExit(
            "API did not exit after SIGTERM; inspect process before taking further action"
        )
    STATE.unlink(missing_ok=True)
    print("Owned PathAble API stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop"])
    (start if parser.parse_args().action == "start" else stop)()
