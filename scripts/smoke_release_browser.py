#!/usr/bin/env python3
"""Exercise the built UI through HTTPS with an explicit local-certificate key pin."""

import argparse
import subprocess
from pathlib import Path

from release_support import ROOT, configuration
from smoke_release import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".local/release/config.env")
    args = parser.parse_args()
    config = configuration(args.env)
    check(config)
    subprocess.run(
        [
            "node",
            str(ROOT / "frontend/scripts/check-release.mjs"),
            config[1]["APP_ORIGIN"],
            str(Path(config[1]["RELEASE_TLS_ROOT"]) / "server.crt"),
            str(ROOT / ".local/screenshots/phase7-release.png"),
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
