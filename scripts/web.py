#!/usr/bin/env python3
"""Manage only this checkout's recorded Vite process; leave unrelated listeners alone."""

import argparse
import json
import os
import socket
import subprocess
import time
import urllib.request

from dev import LOCAL, ROOT, identity

STATE = LOCAL / "web-process.json"
PORT = int(os.environ.get("FRONTEND_PORT", "5173"))


def owned():
    if not STATE.exists():
        return None
    state = json.loads(STATE.read_text())
    current = identity(state["pid"])
    if (
        current
        and current == state["identity"]
        and "node_modules/vite/bin/vite.js" in current
    ):
        return state
    if current:
        raise SystemExit(
            "Recorded web PID belongs to another process; refusing to signal it"
        )
    return None


def ready():
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/src/main.tsx", timeout=2
        ) as response:
            return response.status == 200 and "createRoot" in response.read().decode()
    except (OSError, ValueError):
        return False


def start():
    if owned():
        if ready():
            print("Existing PathAble frontend is ready")
            return
        raise SystemExit("Owned frontend is not ready; inspect .local/web.log")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", PORT))
        except OSError:
            raise SystemExit(
                f"Port {PORT} is occupied; no unrelated process was stopped"
            ) from None
    LOCAL.mkdir(exist_ok=True)
    descriptor = os.open(
        LOCAL / "web.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600
    )
    with os.fdopen(descriptor, "a") as log:
        process = subprocess.Popen(
            [
                "node",
                str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                str(PORT),
                "--strictPort",
            ],
            cwd=ROOT / "frontend",
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    # Popen can expose a transient pre-exec command such as [node]. Persist only
    # the Vite identity, which the ownership guard can recognize on the next call.
    recorded = False
    for _ in range(100):
        if process.poll() is not None:
            raise SystemExit("Frontend exited; inspect .local/web.log")
        if not recorded:
            current = identity(process.pid)
            if current and "node_modules/vite/bin/vite.js" in current:
                STATE.write_text(
                    json.dumps({"pid": process.pid, "identity": current, "port": PORT}) + "\n"
                )
                recorded = True
        if recorded and ready():
            print("PathAble frontend started and its application entry compiles")
            return
        time.sleep(0.2)
    raise SystemExit("Frontend readiness timed out; inspect .local/web.log")


def stop():
    state = owned()
    if not state:
        print("No frontend process owned by this checkout is running")
        return
    process = state["pid"]
    os.kill(process, 15)
    for _ in range(50):
        if not identity(process):
            STATE.unlink(missing_ok=True)
            print("Owned PathAble frontend stopped")
            return
        time.sleep(0.1)
    raise SystemExit("Frontend did not exit; inspect it before taking further action")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop"])
    (start if parser.parse_args().action == "start" else stop)()
