import os
import secrets
import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.cli import prepare_database
from app.core.config import get_settings
from app.db.session import engine
from app.main import app
from app.models.entities import Base, Profile, User
from app.services.auth import hasher
from app.services.seed import seed_demo

PASSWORD = "test-only correct horse battery"


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    settings = get_settings()
    original = settings.postgres_db
    name = "pathable_test_" + uuid.uuid4().hex[:12]
    kwargs = settings.database_url(owner=True, database="postgres").translate_connect_args(
        username="user", database="dbname"
    )
    worker_name = "pathable_ml_test_" + uuid.uuid4().hex[:12]
    previous_ml = {
        key: os.environ.get(key)
        for key in ("ML_WORKER_DB_USER", "ML_WORKER_DB_PASSWORD", "ML_ENABLED")
    }
    os.environ["ML_WORKER_DB_USER"] = worker_name
    os.environ["ML_WORKER_DB_PASSWORD"] = secrets.token_urlsafe(32)
    os.environ["ML_ENABLED"] = "false"
    previous = os.environ.get("POSTGRES_DB")
    os.environ["POSTGRES_DB"] = name
    get_settings.cache_clear()
    engine.cache_clear()
    prepare_database()
    yield
    engine().dispose()
    get_settings.cache_clear()
    engine.cache_clear()
    if previous is None:
        os.environ.pop("POSTGRES_DB", None)
    else:
        os.environ["POSTGRES_DB"] = previous
    for key, value in previous_ml.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    assert name.startswith("pathable_test_") and name != original
    with psycopg.connect(**kwargs, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(worker_name)))


@pytest.fixture(autouse=True)
def reset_database(isolated_database):
    assert get_settings().postgres_db.startswith("pathable_test_")
    owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
    tables = ", ".join('"' + name + '"' for name in Base.metadata.tables)
    with owner.begin() as connection:
        connection.execute(text("TRUNCATE " + tables + " CASCADE"))
    owner.dispose()
    with Session(engine()) as db, db.begin():
        seed_demo(db)


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def headers(client):
    result = client.get("/api/v1/auth/session")
    assert result.status_code == 200, result.text
    return {"Origin": get_settings().app_origin, "X-CSRF-Token": result.json()["csrf_token"]}


def login(client, email, password=PASSWORD):
    result = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}, headers=headers(client)
    )
    assert result.status_code == 200, result.text
    return {"Origin": get_settings().app_origin, "X-CSRF-Token": result.json()["csrf_token"]}


@pytest.fixture
def user(client):
    email = "user@example.com"
    result = client.post(
        "/api/v1/auth/register",
        headers=headers(client),
        json={"email": email, "password": PASSWORD, "display_name": "Test user"},
    )
    assert result.status_code == 201, result.text
    return result.json(), login(client, email)


@pytest.fixture
def admin(client):
    with Session(engine()) as db, db.begin():
        row = User(
            normalized_email="admin@example.com",
            display_name="Test admin",
            role="admin",
            password_hash=hasher.hash(PASSWORD),
        )
        db.add(row)
        db.flush()
        db.add(Profile(user_id=row.id))
    return login(client, "admin@example.com")
