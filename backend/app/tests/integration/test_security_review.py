"""Independent security regressions across request and transaction boundaries."""

import base64
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.entities import AdminAction, GraphEvent, PathEdge, User
from app.services import graph
from app.services.seed import demo_id
from app.tests.conftest import headers
from app.tests.integration.test_graph import RAMP, version


@pytest.mark.parametrize("change,status", [("role", 403), ("active", 401), ("auth_version", 401)])
def test_graph_edit_rechecks_authorization_before_mutation(
    client, admin, monkeypatch, change, status
):
    original = graph.edit_resource
    with Session(engine()) as db:
        events_before = db.scalar(select(func.count()).select_from(GraphEvent))

    def revoke(db, resource, data, actor, *args, **kwargs):
        with Session(engine()) as other, other.begin():
            row = other.get(User, actor.id)
            setattr(
                row,
                change,
                {"role": "user", "active": False, "auth_version": row.auth_version + 1}[change],
            )
        return original(db, resource, data, actor, *args, **kwargs)

    monkeypatch.setattr(graph, "edit_resource", revoke)
    result = client.patch(
        f"/api/v1/admin/path-edges/{RAMP}",
        headers=admin,
        json={"availability": "closed", "expected_version": 1, "reason": "Revoked account edit"},
    )
    assert result.status_code == status
    assert version(client) == 1
    with Session(engine()) as db:
        assert db.get(PathEdge, demo_id("edge:ramp-cross")).availability == "open"
        assert db.scalar(select(func.count()).select_from(AdminAction)) == 0
        assert db.scalar(select(func.count()).select_from(GraphEvent)) == events_before


@pytest.mark.parametrize(
    "body,content_type,status",
    [(b"x" * 65537, "application/json", 413), (b"<xml/>", "application/xml", 415)],
    ids=["oversized", "wrong-media-type"],
)
def test_boundary_errors_keep_security_headers(client, body, content_type, status):
    result = client.post(
        "/api/v1/auth/register", content=body, headers={"Content-Type": content_type}
    )
    assert result.status_code == status
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["x-request-id"] == result.json()["request_id"]


def test_non_ascii_csrf_rejected_without_server_error(client):
    h = [
        (key.encode(), value.encode())
        for key, value in headers(client).items()
        if key != "X-CSRF-Token"
    ]
    h.append((b"X-CSRF-Token", b"\xff"))
    result = client.post("/api/v1/auth/logout", headers=h)
    assert result.status_code == 403
    assert result.json()["code"] == "CSRF_INVALID"


def test_database_outage_fails_closed_for_authenticated_write(client, user):
    from sqlalchemy import create_engine

    from app.core.config import get_settings
    from app.db.session import get_db
    from app.main import app

    account, h = user
    unavailable = create_engine(
        get_settings().database_url().set(port=1),
        connect_args={"connect_timeout": 1},
        hide_parameters=True,
    )

    def offline_db():
        with Session(unavailable) as db:
            yield db

    app.dependency_overrides[get_db] = offline_db
    try:
        result = client.patch(
            "/api/v1/me",
            headers=h,
            json={"display_name": "Must not persist", "expected_version": account["row_version"]},
        )
        assert result.status_code == 503
        assert result.json()["code"] == "DATABASE_UNAVAILABLE"
        assert get_settings().app_db_password.get_secret_value() not in result.text
    finally:
        app.dependency_overrides.pop(get_db)
        unavailable.dispose()
    assert client.get("/api/v1/me").json()["display_name"] == account["display_name"]


@pytest.mark.parametrize(
    "change",
    [{"id": 123}, {"id": []}, {"id": None}, {"time": 123}, {"scope": []}],
)
def test_malformed_cursor_fields_are_client_errors(client, change):
    value = {"time": "2026-10-13T00:00:00+00:00", "scope": "campuses", "id": str(demo_id("campus"))}
    cursor = base64.urlsafe_b64encode(json.dumps(value | change).encode()).decode()
    result = client.get("/api/v1/campuses", params={"cursor": cursor})
    assert result.status_code == 400
    assert result.json()["code"] == "INVALID_CURSOR"
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-request-id"] == result.json()["request_id"]


def test_unexpected_failure_rolls_back_and_retains_private_error_headers(client, user, monkeypatch):
    from app.api import routes
    from app.main import app

    account, headers = user
    original = routes.public_user

    def fail_after_write(row):
        if row.display_name == "Uncommitted audit edit":
            raise RuntimeError("PRIVATE_INTERNAL_DIAGNOSTIC_MUST_NOT_REACH_CLIENT")
        return original(row)

    monkeypatch.setattr(routes, "public_user", fail_after_write)
    with TestClient(app, raise_server_exceptions=False) as probe:
        probe.cookies.update(client.cookies)
        result = probe.patch(
            "/api/v1/me",
            headers=headers,
            json={
                "display_name": "Uncommitted audit edit",
                "expected_version": account["row_version"],
            },
        )
    assert result.status_code == 500
    assert result.json()["code"] == "INTERNAL_ERROR"
    assert "PRIVATE_INTERNAL_DIAGNOSTIC" not in result.text
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["x-content-type-options"] == "nosniff"
    assert result.headers["x-request-id"] == result.json()["request_id"]
    assert client.get("/api/v1/me").json() == account
