#!/usr/bin/env python3
"""Create an isolated localhost HTTPS release fixture; never overwrite configuration."""

import argparse
import os
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / ".local/release")
    parser.add_argument("--project", default="pathable-release")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--local-test", action="store_true", required=True)
    args = parser.parse_args()
    from release_support import validate_project

    validate_project(args.project)
    if not 1024 <= args.port <= 65535:
        parser.error("Choose an unprivileged port")
    root = args.directory.resolve()
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    root.chmod(0o700)
    for name in ("uploads", "models", "tls"):
        (root / name).mkdir(mode=0o700)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:3072",
            "-sha256",
            "-noenc",
            "-keyout",
            str(root / "tls/server.key"),
            "-out",
            str(root / "tls/server.crt"),
            "-days",
            "2",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    (root / "tls/server.key").chmod(0o600)
    (root / "tls/server.crt").chmod(0o644)
    uid, gid = os.getuid(), os.getgid()
    if uid == 0:
        raise SystemExit("Run this local fixture generator as a non-root user")
    values = {
        "RELEASE_PROJECT": args.project,
        "RELEASE_UID": str(uid),
        "RELEASE_GID": str(gid),
        "RELEASE_BIND": "127.0.0.1",
        "RELEASE_HTTPS_PORT": str(args.port),
        "APP_ORIGIN": f"https://localhost:{args.port}",
        "POSTGRES_DB": "pathable",
        "POSTGRES_USER": "pathable_owner",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "APP_DB_USER": "pathable_app",
        "APP_DB_PASSWORD": secrets.token_urlsafe(32),
        "CSRF_SECRET": secrets.token_urlsafe(32),
        "RATE_LIMIT_HASH_KEY": secrets.token_urlsafe(32),
        "ML_WORKER_DB_USER": "pathable_ml_worker",
        "RELEASE_UPLOAD_ROOT": str(root / "uploads"),
        "RELEASE_MODEL_ROOT": str(root / "models"),
        "RELEASE_TLS_ROOT": str(root / "tls"),
        "RELEASE_CA_FILE": str(root / "tls/server.crt"),
    }
    descriptor = os.open(root / "config.env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        stream.write("# LOCAL TEST ONLY: two-day self-signed TLS; not a public deployment.\n")
        for name, value in values.items():
            stream.write(f"{name}={value}\n")
    print("Private localhost release fixture created; secrets were not printed.")


if __name__ == "__main__":
    main()
