from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.models.entities import AuthSession, User
from app.services.auth import hash_token
from app.tests.conftest import PASSWORD, headers, login


def test_readiness_route_method_and_later_phases_are_absent(client):
    assert client.get("/api/v1/health/live").json() == {"status": "alive"}
    assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
    assert client.get("/api/v1/reports").status_code == 401
    assert client.get("/api/v1/routes/calculate").status_code == 405
    assert client.get("/api/v1/ml/status").json() == {
        "available": False,
        "reason": "DISABLED",
        "model_version_id": None,
        "model_name": None,
    }


def test_registration_login_rotation_and_logout(client):
    h = headers(client)
    old_cookie = client.cookies[get_settings().cookie_name]
    r = client.post(
        "/api/v1/auth/register",
        headers=h,
        json={"email": " User@Example.COM ", "password": PASSWORD, "display_name": " User "},
    )
    assert r.status_code == 201 and r.json()["email"] == "user@example.com"
    assert r.json()["role"] == "user" and "password_hash" not in r.json()
    assert client.get("/api/v1/me").status_code == 401
    h = login(client, "user@example.com")
    assert client.cookies[get_settings().cookie_name] != old_cookie
    current = client.cookies[get_settings().cookie_name]
    assert client.get("/api/v1/me").status_code == 200
    client.cookies.clear()
    client.cookies.set(get_settings().cookie_name, old_cookie)
    assert client.get("/api/v1/me").status_code == 401
    client.cookies.set(get_settings().cookie_name, current)
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 204
    assert client.post("/api/v1/auth/logout", headers=h).status_code == 204
    client.cookies.set(get_settings().cookie_name, current)
    assert client.get("/api/v1/me").status_code == 401


@pytest.mark.parametrize(
    "override", [{"Origin": "https://evil.example"}, {"X-CSRF-Token": "bad"}, {"Origin": ""}]
)
def test_csrf_enforced(client, override):
    h = {**headers(client), **override}
    assert (
        client.post(
            "/api/v1/auth/register",
            headers=h,
            json={"email": "user@example.com", "password": PASSWORD, "display_name": "User"},
        ).status_code
        == 403
    )
    with Session(engine()) as db:
        assert db.scalar(select(User).where(User.normalized_email == "user@example.com")) is None


def test_no_mass_assignment_or_password_echo(client):
    payload = {
        "email": "user@example.com",
        "password": PASSWORD,
        "display_name": "User",
        "role": "admin",
    }
    r = client.post("/api/v1/auth/register", headers=headers(client), json=payload)
    assert r.status_code == 422 and PASSWORD not in r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["request_id"] == r.headers["x-request-id"]


def test_duplicate_normalized_email(client, user):
    r = client.post(
        "/api/v1/auth/register",
        headers=headers(client),
        json={"email": "USER@example.com", "password": PASSWORD, "display_name": "Duplicate"},
    )
    assert r.status_code == 409


@pytest.mark.parametrize("mutation", ["expired", "idle", "inactive", "auth_version"])
def test_session_invalidations(client, user, mutation):
    with Session(engine()) as db, db.begin():
        token = client.cookies[get_settings().cookie_name]
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
        now = db.scalar(select(func.clock_timestamp()))
        if mutation == "expired":
            session.expires_at = now - timedelta(seconds=1)
        elif mutation == "idle":
            session.last_seen_at = now - timedelta(hours=25)
        else:
            account = db.get(User, session.user_id)
            if mutation == "inactive":
                account.active = False
            else:
                account.auth_version += 1
    assert client.get("/api/v1/me").status_code == 401


def test_failed_login_rate_limit_is_durable(client):
    h = headers(client)
    body = {"email": "absent@example.com", "password": PASSWORD}
    results = [client.post("/api/v1/auth/login", headers=h, json=body) for _ in range(6)]
    assert [r.status_code for r in results] == [401] * 5 + [429]
    assert "Retry-After" in results[-1].headers


def test_body_limit_and_malformed_json(client):
    assert client.post("/api/v1/auth/register", content=b"x" * 65537).status_code == 413
    r = client.post(
        "/api/v1/auth/register", content="{", headers={"content-type": "application/json"}
    )
    assert r.status_code == 400
    assert (
        client.post(
            "/api/v1/auth/register", content="<xml/>", headers={"content-type": "application/xml"}
        ).status_code
        == 415
    )


def test_profile_cas_and_null_semantics(client, user):
    _, h = user
    value = client.get("/api/v1/me/accessibility-profile").json()
    assert value["unknown_policy"] == "exclude"
    payload = {
        key: value[key]
        for key in (
            "avoid_stairs",
            "max_slope_pct",
            "min_width_m",
            "excluded_surfaces",
            "unknown_policy",
            "travel_speed_mps",
        )
    }
    payload.update(max_slope_pct=None, min_width_m=None, expected_version=value["row_version"])
    r = client.put("/api/v1/me/accessibility-profile", headers=h, json=payload)
    assert r.status_code == 200 and r.json()["max_slope_pct"] is None
    assert r.json()["row_version"] == value["row_version"] + 1
    assert (
        client.put("/api/v1/me/accessibility-profile", headers=h, json=payload).status_code == 409
    )
    payload.update(expected_version=r.json()["row_version"], travel_speed_mps=0)
    assert (
        client.put("/api/v1/me/accessibility-profile", headers=h, json=payload).status_code == 422
    )


def test_edit_display_name_version(client, user):
    account, h = user
    body = {"display_name": "New name", "expected_version": account["row_version"]}
    result = client.patch("/api/v1/me", json=body, headers=h)
    assert result.status_code == 200 and result.json()["display_name"] == "New name"
    assert client.patch("/api/v1/me", json=body, headers=h).status_code == 409


def test_sessions_are_hashed_and_cookie_flags(client):
    r = client.get("/api/v1/auth/session")
    cookie = r.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Path=/" in cookie
    token = client.cookies[get_settings().cookie_name]
    with Session(engine()) as db:
        stored = db.scalar(select(AuthSession))
        assert stored.token_hash == hash_token(token) and stored.token_hash != token
    assert r.headers["cache-control"] == "no-store"
    assert headers(client)["X-CSRF-Token"] == headers(client)["X-CSRF-Token"]


def test_password_whitespace_is_preserved(client):
    secret = "  password spaces are significant  "
    body = {"email": "spaces@example.com", "password": secret, "display_name": "Spaces"}
    assert (
        client.post("/api/v1/auth/register", headers=headers(client), json=body).status_code == 201
    )
    h = headers(client)
    assert (
        client.post(
            "/api/v1/auth/login",
            headers=h,
            json={"email": body["email"], "password": secret.strip()},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login", headers=h, json={"email": body["email"], "password": secret}
        ).status_code
        == 200
    )


def test_concurrent_registration_unique_email(client):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from fastapi.testclient import TestClient

    from app.main import app

    barrier = Barrier(2)

    def register_once(_):
        with TestClient(app) as other:
            h = headers(other)
            barrier.wait(timeout=10)
            return other.post(
                "/api/v1/auth/register",
                headers=h,
                json={"email": "race@example.com", "password": PASSWORD, "display_name": "Race"},
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(register_once, range(2))) == [201, 409]


def test_database_unavailable_is_structured_503(client):
    from sqlalchemy import create_engine

    from app.db.session import get_db
    from app.main import app

    bad = create_engine(
        get_settings().database_url().set(port=1),
        connect_args={"connect_timeout": 1},
        hide_parameters=True,
    )

    def offline_db():
        with Session(bad) as db:
            yield db

    app.dependency_overrides[get_db] = offline_db
    try:
        result = client.get("/api/v1/health/ready")
        assert result.status_code == 503 and result.json()["code"] == "DATABASE_UNAVAILABLE"
        assert get_settings().app_db_password.get_secret_value() not in result.text
    finally:
        app.dependency_overrides.clear()
        bad.dispose()
