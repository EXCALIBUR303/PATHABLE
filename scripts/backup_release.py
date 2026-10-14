#!/usr/bin/env python3
"""Coordinated private DB/file backup and fail-closed restore into an empty release target."""

import argparse
import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from release_support import ROOT, compose, configuration, operator_lock, running, validate_project


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def copy_private(source, destination, *, owner=None):
    source = Path(source)
    destination.mkdir(mode=0o700)
    for path in source.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Private storage must contain only regular files/directories")
        target = destination / path.relative_to(source)
        if path.is_dir():
            target.mkdir(mode=0o700, exist_ok=True)
        else:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            target.chmod(0o600)
    if owner is not None:
        # Staging must be readable by the configured runtime identity, including
        # when a root operator performs recovery for a different service user.
        for path in [*destination.rglob("*"), destination]:
            if (path.stat().st_uid, path.stat().st_gid) != owner:
                os.chown(path, *owner)


def database_command(config, executable, *args, **kwargs):
    values = config[1]
    return compose(
        config,
        "exec",
        "-T",
        "db",
        executable,
        "-U",
        values["POSTGRES_USER"],
        "-d",
        values["POSTGRES_DB"],
        *args,
        **kwargs,
    )


def backup(config, output):
    values = config[1]
    output = output.resolve()
    for name in ("RELEASE_UPLOAD_ROOT", "RELEASE_MODEL_ROOT"):
        if output.is_relative_to(Path(values[name])):
            raise ValueError("Backup output must be outside live private storage")
    output.mkdir(parents=True, mode=0o700, exist_ok=False)
    output.chmod(0o700)
    started = running(config) & {"api", "web"}
    if "ops" in running(config):
        raise ValueError("Wait for operator maintenance/migration to finish")
    try:
        if started:
            compose(config, "stop", "web", "api")
        # Only this serialized operator workflow may run writers; ML is disabled.
        with (output / "database.dump").open("xb") as stream:
            database_command(
                config, "pg_dump", "--format=custom", "--no-owner", "--no-acl", stdout=stream
            )
        (output / "database.dump").chmod(0o600)
        copy_private(values["RELEASE_UPLOAD_ROOT"], output / "uploads")
        copy_private(values["RELEASE_MODEL_ROOT"], output / "models")
        revision = database_command(
            config,
            "psql",
            "-Atc",
            "SELECT version_num FROM alembic_version",
            capture_output=True,
            text=True,
        ).stdout.strip()
        entries = {
            str(path.relative_to(output)): {"sha256": digest(path), "bytes": path.stat().st_size}
            for path in sorted(output.rglob("*"))
            if path.is_file()
        }
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(UTC).isoformat(),
            "migration_revision": revision,
            "source_project": values["RELEASE_PROJECT"],
            "files": entries,
            "limitations": "Private operator backup; checksums detect corruption, not authenticity. All external writers must be stopped. Credentials/TLS are excluded and must be restored separately.",
        }
        descriptor = os.open(output / "manifest.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(manifest, stream, indent=2)
            stream.write("\n")
        print("Coordinated private backup completed; checksum manifest recorded.")
    finally:
        if started:
            compose(config, "up", "-d", "--wait", *sorted(started))


def verify_backup(source):
    source = source.resolve(strict=True)
    manifest_path = source / "manifest.json"
    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
        or manifest_path.stat().st_size > 8 * 1024 * 1024
    ):
        raise ValueError("Invalid backup manifest")
    manifest = json.loads(manifest_path.read_text())
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {
            "schema_version",
            "created_at",
            "migration_revision",
            "source_project",
            "files",
            "limitations",
        }
        or type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or not isinstance(manifest["files"], dict)
    ):
        raise ValueError("Unsupported backup manifest")
    if (
        not isinstance(manifest["migration_revision"], str)
        or not re.fullmatch(r"[a-zA-Z0-9_]{1,32}", manifest["migration_revision"])
        or not isinstance(manifest["created_at"], str)
        or not datetime.fromisoformat(manifest["created_at"]).tzinfo
        or not isinstance(manifest["source_project"], str)
        or not isinstance(manifest["limitations"], str)
        or not manifest["limitations"].strip()
    ):
        raise ValueError("Invalid backup metadata")
    validate_project(manifest["source_project"])
    for value in manifest["files"].values():
        if (
            not isinstance(value, dict)
            or set(value) != {"sha256", "bytes"}
            or type(value["bytes"]) is not int
            or value["bytes"] < 0
            or not isinstance(value["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
        ):
            raise ValueError("Invalid backup file metadata")
    actual = set()
    for path in source.rglob("*"):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError("Backup contains an unsafe filesystem entry")
        if path.is_file() and path != manifest_path:
            actual.add(str(path.relative_to(source)))
    if actual != set(manifest["files"]) or "database.dump" not in actual:
        raise ValueError("Backup files differ from the manifest")
    for name, value in manifest["files"].items():
        if name != "database.dump" and not name.startswith(("uploads/", "models/")):
            raise ValueError("Unexpected backup path")
        path = (source / name).resolve(strict=True)
        if (
            not path.is_relative_to(source)
            or path.stat().st_size != value["bytes"]
            or digest(path) != value["sha256"]
        ):
            raise ValueError("Backup checksum/size verification failed")
    if not (source / "uploads").is_dir() or not (source / "models").is_dir():
        raise ValueError("Missing private storage directories")
    return source, manifest


def restore(config, source):
    source, manifest = verify_backup(source)
    values = config[1]
    if running(config) & {"api", "web", "ops"}:
        raise ValueError("Restore requires stopped application/operator services")
    targets = [Path(values[name]) for name in ("RELEASE_UPLOAD_ROOT", "RELEASE_MODEL_ROOT")]
    if any(list(path.iterdir()) for path in targets):
        raise ValueError(
            "Restore requires empty private storage; existing data is never overwritten"
        )
    owner = (int(values.get("RELEASE_UID", "10001")), int(values.get("RELEASE_GID", "10001")))
    if os.geteuid() != 0 and owner != (os.geteuid(), os.getegid()):
        raise ValueError("Restore must run as the configured runtime UID/GID or a root operator")
    compose(config, "up", "-d", "--wait", "db")
    found = compose(
        config,
        "exec",
        "-T",
        "db",
        "psql",
        "-U",
        values["POSTGRES_USER"],
        "-d",
        "postgres",
        "-Atc",
        f"SELECT count(*) FROM pg_database WHERE datname='{values['POSTGRES_DB']}'",
        capture_output=True,
        text=True,
    ).stdout.strip()
    if found == "0":
        compose(
            config,
            "exec",
            "-T",
            "db",
            "createdb",
            "-U",
            values["POSTGRES_USER"],
            "--template=template0",
            "--owner=" + values["POSTGRES_USER"],
            values["POSTGRES_DB"],
        )
    schemas = database_command(
        config,
        "psql",
        "-Atc",
        "SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' AND nspname NOT IN ('public','information_schema')",
        capture_output=True,
        text=True,
    ).stdout.strip()
    if schemas != "0":
        raise ValueError("Restore requires a pristine application database without other schemas")
    query = "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype='e')"
    count = database_command(
        config, "psql", "-Atc", query, capture_output=True, text=True
    ).stdout.strip()
    if count != "0":
        raise ValueError(
            "Restore requires an empty application database; existing data is never overwritten"
        )
    stages = [path.parent / (".restore-" + uuid.uuid4().hex) for path in targets]
    try:
        for name, stage in zip(("uploads", "models"), stages, strict=True):
            copy_private(source / name, stage, owner=owner)
        with (source / "database.dump").open("rb") as stream:
            database_command(
                config,
                "pg_restore",
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-acl",
                stdin=stream,
            )
        for stage, target in zip(stages, targets, strict=True):
            target.rmdir()
            os.replace(stage, target)
        # Restored data uses this target's current private role credentials/grants.
        compose(config, "run", "--rm", "-T", "ops", "python", "-m", "app.cli", "prepare-db")
        revision = database_command(
            config,
            "psql",
            "-Atc",
            "SELECT version_num FROM alembic_version",
            capture_output=True,
            text=True,
        ).stdout.strip()
        if revision != manifest["migration_revision"]:
            raise ValueError(
                "Restore upgraded the schema; validate the upgrade before starting services"
            )
        print(
            "Backup restored into empty release storage/database; services remain stopped for review."
        )
    finally:
        for stage in stages:
            if stage.exists():
                shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".local/release/config.env")
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("backup")
    create.add_argument("--output", type=Path, required=True)
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    config = configuration(args.env)
    with operator_lock(config):
        if args.action == "backup":
            backup(config, args.output)
        else:
            restore(config, args.source)


if __name__ == "__main__":
    main()
