#!/usr/bin/env python3
"""Real HTTPS account/evidence → coordinated snapshot → fresh isolated restore → restart."""

import argparse
import base64
import json
import secrets
import socket
import subprocess
import sys
import uuid
from pathlib import Path

from backup_release import backup, restore, verify_backup
from release_support import ROOT, compose, configuration, operator_lock
from smoke_release import check, client_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".local/release/config.env")
    args = parser.parse_args()
    source = configuration(args.env)
    check(source)
    identity = uuid.uuid4().hex[:10]
    email, password = f"restore-{identity}@example.com", secrets.token_urlsafe(32)
    with client_for(source) as client:
        anonymous = client.get("/auth/session").json()
        headers = {"Origin": source[1]["APP_ORIGIN"], "X-CSRF-Token": anonymous["csrf_token"]}
        registration = client.post(
            "/auth/register",
            headers=headers,
            json={
                "email": email,
                "password": password,
                "display_name": "Synthetic restore explorer",
            },
        )
        assert registration.status_code == 201
        user_id = registration.json()["id"]
        session = client.post(
            "/auth/login", headers=headers, json={"email": email, "password": password}
        )
        assert session.status_code == 200
        headers["X-CSRF-Token"] = session.json()["csrf_token"]
        profile = client.get("/me/accessibility-profile").json()
        profile_input = {
            key: profile[key]
            for key in (
                "avoid_stairs",
                "max_slope_pct",
                "min_width_m",
                "excluded_surfaces",
                "unknown_policy",
                "travel_speed_mps",
            )
        }
        profile_input.update(min_width_m=1.1, expected_version=profile["row_version"])
        assert (
            client.put("/me/accessibility-profile", headers=headers, json=profile_input).status_code
            == 200
        )
        campus = client.get("/campuses").json()["items"][0]
        location = client.get("/locations", params={"campus_id": campus["id"]}).json()["items"][0]
        saved = client.post(
            "/me/saved-destinations", headers=headers, json={"location_id": location["id"]}
        )
        assert saved.status_code == 201
        report = client.post(
            "/reports",
            headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
            json={
                "campus_id": campus["id"],
                "location_id": location["id"],
                "point": location["point"],
                "category": "other_accessibility_concern",
                "description": "Synthetic coordinated backup and restore concern",
            },
        )
        assert report.status_code == 201
        report = report.json()
        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        uploaded = client.post(
            f"/reports/{report['id']}/evidence",
            headers=headers,
            data={"expected_version": str(report["row_version"])},
            files={"file": ("synthetic.png", image, "image/png")},
        )
        assert uploaded.status_code == 201, uploaded.text
        evidence = uploaded.json()
        content_url = f"/reports/{report['id']}/evidence/{evidence['id']}/content"
        content = client.get(content_url).content
        graph_before = client.get(f"/campuses/{campus['id']}/graph").json()
    # A labeled inert asset proves storage preservation without an enabled model.
    marker = Path(source[1]["RELEASE_MODEL_ROOT"]) / f"restore-probe-{identity}.txt"
    marker.write_text("INERT SYNTHETIC BACKUP PROBE; NOT A MODEL\n")
    marker.chmod(0o600)
    snapshot = ROOT / ".local" / f"release-backup-{identity}"
    target_root = ROOT / ".local" / f"release-restore-{identity}"
    with operator_lock(source):
        backup(source, snapshot)
    check(source)
    _, manifest = verify_backup(snapshot)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/configure_release.py"),
            "--local-test",
            "--directory",
            str(target_root),
            "--project",
            f"pathable-release-restore-{identity}",
            "--port",
            str(port),
        ],
        check=True,
    )
    target = configuration(target_root / "config.env")
    try:
        with operator_lock(target):
            restore(target, snapshot)
            compose(target, "up", "-d", "--wait", "db", "api", "web")
        check(target)
        with client_for(target) as client:
            session = client.get("/auth/session").json()
            h = {"Origin": target[1]["APP_ORIGIN"], "X-CSRF-Token": session["csrf_token"]}
            login = client.post(
                "/auth/login", headers=h, json={"email": email, "password": password}
            )
            assert login.status_code == 200 and login.json()["user"]["id"] == user_id
            assert client.get("/me/accessibility-profile").json()["min_width_m"] == 1.1
            assert any(
                item["id"] == saved.json()["id"]
                for item in client.get("/me/saved-destinations").json()["items"]
            )
            restored = client.get(f"/reports/{report['id']}").json()
            assert (
                restored["status"] == "pending_review"
                and restored["evidence"][0]["sha256"] == evidence["sha256"]
            )
            assert client.get(content_url).content == content
            graph_after = client.get(f"/campuses/{campus['id']}/graph").json()
            assert graph_after["features"] == graph_before["features"]
            assert graph_after["graph_version"] == graph_before["graph_version"]
            assert graph_after["data_origin"] == graph_before["data_origin"]
        assert (
            Path(target[1]["RELEASE_MODEL_ROOT"]) / marker.name
        ).read_bytes() == marker.read_bytes()
        compose(target, "restart", "db", "api", "web")
        compose(target, "up", "-d", "--wait", "db", "api", "web")
        check(target)
        # Refuse to overwrite the now-populated target.
        compose(target, "stop", "api", "web")
        try:
            restore(target, snapshot)
        except ValueError as error:
            assert "empty private storage" in str(error)
        else:
            raise AssertionError("A populated restore target was accepted")
        print(
            "PASS coordinated restore: actual user/profile/saved place/report/private image/graph/model-storage bytes; retained restart; populated-target refusal"
        )
        summary = {
            "source_project": source[1]["RELEASE_PROJECT"],
            "restored_project": target[1]["RELEASE_PROJECT"],
            "migration_revision": manifest["migration_revision"],
            "backup_file_count": len(manifest["files"]),
            "result": "passed",
            "scope": "synthetic local release fixture, not trained ML or remote deployment",
        }
        (ROOT / ".local/release-restore-result.json").write_text(
            json.dumps(summary, indent=2) + "\n"
        )
    finally:
        compose(target, "stop")
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
