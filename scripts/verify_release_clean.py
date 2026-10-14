#!/usr/bin/env python3
"""Build/start a clean nonignored source export, without development configuration/caches."""

import json
import shutil
import socket
import subprocess
import sys
import uuid

from release_support import ROOT


def main():
    if shutil.disk_usage(ROOT).free < 8 * 1024**3:
        raise ValueError("Clean rebuild needs at least 8 GiB free; no existing data was changed")
    identity = uuid.uuid4().hex[:10]
    export = ROOT / ".local" / ("release-clean-" + identity)
    export.mkdir(mode=0o700)
    paths = (
        subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    for name in paths:
        if not name:
            continue
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("Source export accepts only regular repository files")
        target = export / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assert not (export / ".env").exists() and not (export / ".venv").exists()
    artifact_root = export / ".local/release-build"
    artifact_root.mkdir(parents=True)
    for name in ("wheels", "npm-cache/_cacache"):
        shutil.copytree(ROOT / ".local/release-build" / name, artifact_root / name)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    fixture = export / ".local/release"
    subprocess.run(
        [
            sys.executable,
            str(export / "scripts/configure_release.py"),
            "--local-test",
            "--project",
            f"pathable-release-clean-{identity}",
            "--port",
            str(port),
        ],
        check=True,
    )
    command = [sys.executable, str(export / "scripts/release.py")]
    try:
        subprocess.run([*command, "build", "--no-cache", "--discard-build-cache"], check=True)
        subprocess.run([*command, "init", "--synthetic"], check=True)
        subprocess.run([*command, "start"], check=True)
        subprocess.run([sys.executable, str(export / "scripts/smoke_release.py")], check=True)
        print(
            "PASS clean source export: no development env/venv/node_modules, no-cache offline images, fresh migration/seed and strict HTTPS functional checks"
        )
        (ROOT / ".local/release-clean-result.json").write_text(
            json.dumps(
                {
                    "source_export": str(export.relative_to(ROOT)),
                    "result": "passed",
                    "scope": "Local nonignored source export; remote Git clone/CI execution not verified",
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        if (fixture / "config.env").exists():
            subprocess.run([*command, "stop", "--all"], check=True)
        # Only this export's verified cache copies are disposable; retain source,
        # private configuration, files and DB volume for inspection.
        if artifact_root.exists():
            shutil.rmtree(artifact_root)


if __name__ == "__main__":
    main()
