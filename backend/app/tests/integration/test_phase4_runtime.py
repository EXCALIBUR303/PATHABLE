"""Retention, interrupted uploads, ownership and genuine migration upgrade checks."""

import os
import subprocess
import sys
import uuid
from datetime import UTC
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.models.entities import GraphEvent
from app.models.reporting import IdempotencyRecord, ObstacleReport, ReportEvidence
from app.services import evidence, maintenance
from app.services.seed import demo_id
from app.tests.conftest import PASSWORD, headers, login
from app.tests.integration.test_evidence import upload
from app.tests.integration.test_reporting import CID, submit


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_root", tmp_path / "private-evidence")


def test_other_owner_cannot_read_upload_delete_or_list_private_evidence(client, user):
    _, h = user
    row = submit(client, h)
    response = upload(client, h, row)
    assert response.status_code == 201, response.text
    item = response.json()
    response = client.post(
        "/api/v1/auth/register",
        headers=headers(client),
        json={"email": "other@example.com", "display_name": "Other owner", "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    other = login(client, "other@example.com")
    assert client.get(f"/api/v1/reports/{row['id']}").status_code == 404
    assert (
        client.get(f"/api/v1/reports/{row['id']}/evidence/{item['id']}/content").status_code == 404
    )
    assert upload(client, other, {**row, "row_version": 3}).status_code == 404
    assert (
        client.request(
            "DELETE",
            f"/api/v1/reports/{row['id']}/evidence/{item['id']}",
            headers=other,
            json={"expected_version": 3},
        ).status_code
        == 404
    )
    assert client.get("/api/v1/reports").json()["items"] == []


@pytest.mark.parametrize("declared_length", [None, "1"])
def test_actual_multipart_bytes_remain_bounded_without_truthful_content_length(
    client, user, declared_length
):
    _, h = user
    row = submit(client, h)
    boundary = "bounded-evidence-test"
    prefix = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="expected_version"\r\n\r\n1\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n'
    ).encode()
    chunks = [prefix, b"x" * (evidence.MAX_REQUEST_BYTES + 1), f"\r\n--{boundary}--\r\n".encode()]
    request_headers = {**h, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    if declared_length:
        request_headers["Content-Length"] = declared_length
    response = client.post(
        f"/api/v1/reports/{row['id']}/evidence", headers=request_headers, content=iter(chunks)
    )
    assert response.status_code == 413, response.text
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(ReportEvidence)) == 0


def test_decoder_timeout_releases_reservation_and_never_publishes_content(
    client, user, monkeypatch
):
    _, h = user
    row = submit(client, h)

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("bounded image worker", 6)

    monkeypatch.setattr(evidence.subprocess, "run", timeout)
    response = upload(client, h, row)
    assert response.status_code == 422 and response.json()["code"] == "IMAGE_PROCESSING_FAILED"
    with Session(engine()) as db:
        item = db.scalar(select(ReportEvidence))
        assert item.status == "rejected" and item.failure_code == "IMAGE_PROCESSING_FAILED"
    assert not list(get_settings().private_upload_root.iterdir())


def test_owner_retention_prunes_only_old_events_and_private_orphans_preserving_ready_images(
    client, user
):
    _, h = user
    row = submit(client, h)
    item = upload(client, h, row).json()
    settings = get_settings()
    owner = create_engine(settings.database_url(owner=True), hide_parameters=True)
    with owner.begin() as connection:
        # Construct an old committed fixture without modifying append-only events.
        connection.execute(text("TRUNCATE graph_events"))
        connection.execute(
            text(
                "INSERT INTO graph_events(campus_id,graph_version,event_type,changed_edge_ids,reason,occurred_at) VALUES (:campus,1,'graph.reset','{}'::uuid[],'old_fixture',clock_timestamp()-interval '8 days'),(:campus,2,'graph.updated','{}'::uuid[],'recent_fixture',clock_timestamp())"
            ),
            {"campus": CID},
        )
        connection.execute(text("UPDATE graph_state SET version=2"))
        connection.execute(
            text("UPDATE idempotency_records SET expires_at=clock_timestamp()-interval '1 hour'")
        )
        actor = uuid.UUID(row["reporter_id"])
        interrupted = uuid.uuid4()
        connection.execute(
            text(
                "INSERT INTO report_evidence(id,report_id,uploader_id,storage_key,media_type,byte_size,status,created_at) VALUES (:id,:report,:actor,:key,'image/png',10485760,'processing',clock_timestamp()-interval '25 hours')"
            ),
            {
                "id": interrupted,
                "report": row["id"],
                "actor": actor,
                "key": interrupted.hex + ".png",
            },
        )
    owner.dispose()
    with Session(engine()) as db:
        ready_key = db.get(ReportEvidence, uuid.UUID(item["id"])).storage_key
    root = settings.private_upload_root
    orphan = root / (uuid.uuid4().hex + ".input")
    orphan.write_bytes(b"private interrupted input")
    old = datetime_now_timestamp() - 26 * 3600
    os.utime(orphan, (old, old))
    ready = evidence.content_path(ready_key)
    os.utime(ready, (old, old))
    removed = maintenance.maintain()
    assert removed["graph_events"] == 1 and removed["idempotency_records"] == 1
    assert removed["interrupted_uploads"] == 1 and removed["private_orphan_files"] == 1
    assert ready.is_file() and not orphan.exists()
    with Session(engine()) as db:
        assert db.get(GraphEvent, (demo_id("campus"), 1)) is None
        assert db.get(GraphEvent, (demo_id("campus"), 2)) is not None
        assert db.get(ReportEvidence, interrupted).status == "rejected"
        assert db.get(ReportEvidence, uuid.UUID(item["id"])).status == "ready"
        assert db.scalar(select(func.count()).select_from(IdempotencyRecord)) == 0
    with pytest.raises(DBAPIError), Session(engine()) as db, db.begin():
        db.execute(text("DELETE FROM graph_events"))


def datetime_now_timestamp():
    from datetime import datetime

    return datetime.now(UTC).timestamp()


def test_existing_foundation_database_upgrades_preserving_data_and_emits_reset():
    settings = get_settings()
    name = "pathable_upgrade_" + uuid.uuid4().hex[:12]
    kwargs = settings.database_url(owner=True, database="postgres").translate_connect_args(
        username="user", database="dbname"
    )
    with psycopg.connect(**kwargs, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(name), sql.Identifier(settings.postgres_user)
            )
        )
    environment = {**os.environ, "POSTGRES_DB": name}
    backend = Path(__file__).resolve().parents[3]
    program = """
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.services.seed import seed_demo,demo_id
from app.models.entities import GraphEvent,GraphState,PathEdge
command.upgrade(Config('alembic.ini'),'0001_foundation')
owner=create_engine(get_settings().database_url(owner=True),hide_parameters=True)
with Session(owner) as db,db.begin():
    seed_demo(db)
    edge=db.get(PathEdge,demo_id('edge:ramp-cross'))
    edge.availability='closed'
    edge.row_version=2
command.upgrade(Config('alembic.ini'),'head')
with Session(owner) as db:
    assert db.scalar(text('SELECT version_num FROM alembic_version'))=='0003_ml'
    assert db.get(PathEdge,demo_id('edge:ramp-cross')).availability=='closed'
    assert db.get(PathEdge,demo_id('edge:ramp-cross')).row_version==2
    assert db.get(GraphState,demo_id('campus')).version==2
    assert db.get(GraphEvent,(demo_id('campus'),2)).event_type=='graph.reset'
owner.dispose()
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", program],
            cwd=backend,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
    finally:
        with psycopg.connect(**kwargs, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.mark.parametrize("scope,limit", [("report", 10), ("upload", 20)])
def test_hourly_write_quotas_fail_before_domain_changes_with_accurate_retry_after(
    client, user, monkeypatch, scope, limit
):
    from datetime import UTC, datetime

    from app.services import auth

    now = datetime(2026, 10, 13, 12, 0, 20, tzinfo=UTC)
    monkeypatch.setattr(auth, "clock_now", lambda _db: now)
    _, h = user
    row = submit(client, h)
    if scope == "report":
        for _ in range(limit - 1):
            submit(client, h)
        blocked = client.post(
            "/api/v1/reports",
            headers={**h, "Idempotency-Key": str(uuid.uuid4())},
            json={
                "campus_id": CID,
                "category": "blocked_ramp",
                "description": "Fictional quota-bound concern",
                "point": {"type": "Point", "coordinates": [0, 0]},
            },
        )
    else:
        for _ in range(limit):
            rejected = upload(client, h, row, b"<svg/>", "image/svg+xml", "image.svg")
            assert rejected.status_code == 415
        blocked = upload(client, h, row, b"<svg/>", "image/svg+xml", "image.svg")
    assert blocked.status_code == 429 and blocked.headers["Retry-After"] == "3580"
    with Session(engine()) as db:
        assert db.scalar(select(func.count()).select_from(ObstacleReport)) == (
            limit if scope == "report" else 1
        )
        assert db.scalar(select(func.count()).select_from(ReportEvidence)) == 0
