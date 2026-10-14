#!/usr/bin/env python3
"""Explicit local/operator release workflow; does not publish or deploy remotely."""

import argparse
import shutil
from pathlib import Path

from release_support import (
    ROOT,
    build_cache_ids,
    compose,
    configuration,
    discard_build_cache,
    operator_lock,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".local/release/config.env")
    sub = parser.add_subparsers(dest="action", required=True)
    build = sub.add_parser("build")
    build.add_argument("--no-cache", action="store_true")
    build.add_argument("--discard-build-cache", action="store_true")
    stop = sub.add_parser("stop")
    stop.add_argument("--all", action="store_true")
    for name in ("start", "status", "maintenance"):
        sub.add_parser(name)
    init = sub.add_parser("init")
    init.add_argument("--synthetic", action="store_true")
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    args = parser.parse_args()
    config = configuration(args.env)
    with operator_lock(config):
        if args.action == "build":
            if shutil.disk_usage(ROOT).free < 8 * 1024**3:
                raise ValueError(
                    "Release build needs at least 8 GiB free; review disposable build caches before retrying"
                )
            before = build_cache_ids() if args.discard_build_cache else set()
            try:
                compose(config, "build", *(["--no-cache"] if args.no_cache else []), "api", "web")
            finally:
                if args.discard_build_cache:
                    discard_build_cache(build_cache_ids() - before)
        elif args.action == "init":
            compose(config, "up", "-d", "--wait", "db")
            compose(config, "run", "--rm", "-T", "ops", "python", "-m", "app.cli", "prepare-db")
            if args.synthetic:
                compose(
                    config,
                    "run",
                    "--rm",
                    "-T",
                    "ops",
                    "python",
                    "-m",
                    "app.cli",
                    "seed",
                    "--synthetic",
                    "--if-empty",
                )
        elif args.action == "start":
            compose(config, "up", "-d", "--wait", "db", "api", "web")
        elif args.action == "stop":
            compose(config, "stop", *([] if args.all else ["web", "api"]))
        elif args.action == "status":
            compose(config, "ps")
        elif args.action == "maintenance":
            compose(config, "run", "--rm", "-T", "ops", "python", "-m", "app.cli", "maintenance")
        elif args.action == "create-admin":
            compose(
                config,
                "run",
                "--rm",
                "ops",
                "python",
                "-m",
                "app.cli",
                "create-admin",
                "--email",
                args.email,
                "--name",
                args.name,
            )


if __name__ == "__main__":
    main()
