"""Shared safe configuration and Compose execution for operator-only release commands."""

import contextlib
import fcntl
import os
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def validate_project(value):
    if not re.fullmatch(r"pathable-release(?:-[a-z0-9]+)*", value):
        raise ValueError("Release project must be pathable-release or pathable-release-<suffix>")


def configuration(path):
    path = Path(path).resolve(strict=True)
    if path.stat().st_mode & 0o077:
        raise ValueError("Release configuration must have mode 0600")
    values = dict(dotenv_values(path, interpolate=False))
    validate_project(values.get("RELEASE_PROJECT", ""))
    for name in ("RELEASE_UID", "RELEASE_GID"):
        value = values.get(name, "10001")
        if not value.isascii() or not value.isdigit() or int(value) <= 0:
            raise ValueError("Release API/web require non-root numeric UID/GID")
    for name in ("POSTGRES_DB", "POSTGRES_USER", "APP_DB_USER", "ML_WORKER_DB_USER"):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", values.get(name, "")):
            raise ValueError(f"Invalid release identifier: {name}")
    if len({values[name] for name in ("POSTGRES_USER", "APP_DB_USER", "ML_WORKER_DB_USER")}) != 3:
        raise ValueError("Owner, application and ML worker database roles must be distinct")
    for name in ("POSTGRES_PASSWORD", "APP_DB_PASSWORD", "CSRF_SECRET", "RATE_LIMIT_HASH_KEY"):
        if not isinstance(values.get(name), str) or len(values[name]) < 24:
            raise ValueError(f"Missing strong release binding: {name}")
    for name in ("RELEASE_UPLOAD_ROOT", "RELEASE_MODEL_ROOT", "RELEASE_TLS_ROOT"):
        location = Path(values.get(name, "")).resolve(strict=True)
        if not location.is_dir():
            raise ValueError(f"Missing private directory: {name}")
        values[name] = str(location)
    roots = [
        Path(values[name])
        for name in ("RELEASE_UPLOAD_ROOT", "RELEASE_MODEL_ROOT", "RELEASE_TLS_ROOT")
    ]
    if any(a.is_relative_to(b) for i, a in enumerate(roots) for j, b in enumerate(roots) if i != j):
        raise ValueError("Private upload/model/TLS directories must be separate")
    return path, values


def compose(config, *args, **kwargs):
    path, values = config
    environment = dict(os.environ, DOCKER_CONFIG=str(ROOT / ".local/docker"))
    # The private file is authoritative, even if development bindings are exported.
    environment.update({key: value for key, value in values.items() if value is not None})
    command = [
        "docker",
        "compose",
        "--project-name",
        values["RELEASE_PROJECT"],
        "--env-file",
        str(path),
        "-f",
        str(ROOT / "compose.release.yml"),
        *args,
    ]
    return subprocess.run(command, cwd=ROOT, env=environment, check=True, **kwargs)


def running(config):
    result = compose(
        config, "ps", "--status", "running", "--services", capture_output=True, text=True
    )
    return set(result.stdout.split())


def build_cache_ids():
    import json

    environment = dict(os.environ, DOCKER_CONFIG=str(ROOT / ".local/docker"))
    output = subprocess.check_output(
        ["docker", "buildx", "du", "--format", "{{json .}}"], env=environment, text=True
    )
    return {json.loads(line)["ID"] for line in output.splitlines() if line}


def discard_build_cache(ids):
    if not ids:
        return
    environment = dict(os.environ, DOCKER_CONFIG=str(ROOT / ".local/docker"))
    pattern = "^(" + "|".join(re.escape(value) for value in sorted(ids)) + ")$"
    subprocess.run(
        ["docker", "buildx", "prune", "--force", "--all", "--filter", "id~=" + pattern],
        env=environment,
        check=True,
        stdout=subprocess.DEVNULL,
    )


@contextlib.contextmanager
def operator_lock(config):
    path = ROOT / ".local" / (config[1]["RELEASE_PROJECT"] + ".lock")
    path.parent.mkdir(exist_ok=True)
    with path.open("a") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
