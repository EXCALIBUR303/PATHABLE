"""Fail-closed backup manifest parsing; fake dump bytes are never restored by these unit tests."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup_release  # noqa: E402
from backup_release import copy_private, digest, restore, verify_backup  # noqa: E402
from release_support import configuration  # noqa: E402


@pytest.fixture
def snapshot(tmp_path):
    root = tmp_path / "backup"
    root.mkdir()
    (root / "uploads").mkdir()
    (root / "models").mkdir()
    (root / "database.dump").write_bytes(b"EXPLICIT UNIT FIXTURE; NOT A DATABASE DUMP")
    (root / "uploads/image.png").write_bytes(b"EXPLICIT UNIT FIXTURE; NOT AN IMAGE")
    entries = {
        str(p.relative_to(root)): {"sha256": digest(p), "bytes": p.stat().st_size}
        for p in root.rglob("*")
        if p.is_file()
    }
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files": entries,
                "migration_revision": "0003_ml",
                "created_at": "2026-10-13T00:00:00+00:00",
                "source_project": "pathable-release-test",
                "limitations": "UNIT FIXTURE ONLY; never import these bytes",
            }
        )
    )
    return root


def test_valid_manifest_is_checked(snapshot):
    assert verify_backup(snapshot)[0] == snapshot


@pytest.mark.parametrize("failure", ["corruption", "missing", "extra", "traversal", "symlink"])
def test_invalid_snapshot_is_rejected(snapshot, failure, tmp_path):
    if failure == "corruption":
        (snapshot / "database.dump").write_bytes(b"CHANGED")
    elif failure == "missing":
        (snapshot / "uploads/image.png").unlink()
    elif failure == "extra":
        (snapshot / "uploads/extra").write_text("unrecorded")
    elif failure == "symlink":
        (snapshot / "uploads/image.png").unlink()
        (snapshot / "uploads/image.png").symlink_to(tmp_path)
    else:
        manifest = json.loads((snapshot / "manifest.json").read_text())
        manifest["files"]["../outside"] = {"sha256": "0" * 64, "bytes": 1}
        (snapshot / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        verify_backup(snapshot)


@pytest.mark.parametrize(
    "failure",
    [
        "missing_revision",
        "invalid_revision",
        "naive_date",
        "wrong_project",
        "boolean_schema",
        "wrong_shape",
        "negative_bytes",
        "boolean_bytes",
        "bad_hash",
    ],
)
def test_invalid_metadata_refused_before_any_restore_operation(snapshot, monkeypatch, failure):
    path = snapshot / "manifest.json"
    manifest = json.loads(path.read_text())
    if failure == "missing_revision":
        del manifest["migration_revision"]
    elif failure == "invalid_revision":
        manifest["migration_revision"] = []
    elif failure == "naive_date":
        manifest["created_at"] = "2026-10-13T00:00:00"
    elif failure == "wrong_project":
        manifest["source_project"] = "pathable"
    elif failure == "boolean_schema":
        manifest["schema_version"] = True
    elif failure == "wrong_shape":
        manifest = []
    elif failure == "bad_hash":
        manifest["files"]["database.dump"]["sha256"] = "invalid"
    else:
        manifest["files"]["database.dump"]["bytes"] = -1 if failure == "negative_bytes" else True
    path.write_text(json.dumps(manifest))

    def unexpected(*args, **kwargs):
        pytest.fail("Invalid backup must be rejected before contacting or modifying the target")

    monkeypatch.setattr(backup_release, "running", unexpected)
    monkeypatch.setattr(backup_release, "compose", unexpected)
    with pytest.raises(ValueError):
        restore(None, snapshot)


def test_private_staging_preserves_bytes_and_runtime_permissions(snapshot, tmp_path):
    target = tmp_path / "staging"
    copy_private(snapshot / "uploads", target, owner=(os.geteuid(), os.getegid()))
    assert (target / "image.png").read_bytes() == (snapshot / "uploads/image.png").read_bytes()
    assert target.stat().st_mode & 0o777 == 0o700
    assert (target / "image.png").stat().st_mode & 0o777 == 0o600
    assert (target / "image.png").stat().st_uid == os.geteuid()


def test_unprivileged_wrong_runtime_identity_refused_before_database(
    snapshot, tmp_path, monkeypatch
):
    roots = [tmp_path / name for name in ("target-uploads", "target-models")]
    for root in roots:
        root.mkdir()
    config = (
        None,
        {
            "RELEASE_UPLOAD_ROOT": str(roots[0]),
            "RELEASE_MODEL_ROOT": str(roots[1]),
            "RELEASE_UID": "10001",
            "RELEASE_GID": "10001",
        },
    )
    monkeypatch.setattr(backup_release.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(backup_release.os, "getegid", lambda: 1000)
    monkeypatch.setattr(backup_release, "running", lambda config: set())

    def unexpected(*args, **kwargs):
        pytest.fail("Unsupported restore identity must not change the database")

    monkeypatch.setattr(backup_release, "compose", unexpected)
    with pytest.raises(ValueError, match="runtime UID/GID"):
        restore(config, snapshot)
    assert all(not list(root.iterdir()) for root in roots)


def test_operator_role_collision_refused_before_private_storage_access(tmp_path):
    path = tmp_path / "config.env"
    path.write_text(
        "RELEASE_PROJECT=pathable-release-test\nPOSTGRES_DB=pathable\nPOSTGRES_USER=owner\nAPP_DB_USER=owner\nML_WORKER_DB_USER=worker\n"
    )
    path.chmod(0o600)
    with pytest.raises(ValueError, match="roles must be distinct"):
        configuration(path)
