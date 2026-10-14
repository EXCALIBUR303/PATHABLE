#!/usr/bin/env python3
"""Explicit developer check: restart owned API and Compose DB, retaining all volumes."""

import os
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
base = f"http://127.0.0.1:{int(os.environ.get('API_PORT', '8000'))}/api/v1"
email = f"persistence-{uuid.uuid4().hex}@example.com"
password = secrets.token_urlsafe(32)
origin = os.environ.get("APP_ORIGIN", "http://localhost:5173")

with httpx.Client(base_url=base, timeout=15) as client:
    csrf = client.get("/auth/session").json()["csrf_token"]
    headers = {"Origin": origin, "X-CSRF-Token": csrf}
    registration = client.post(
        "/auth/register",
        headers=headers,
        json={"email": email, "password": password, "display_name": "Persistence verification"},
    )
    assert registration.status_code == 201, "Live registration failed"
    account = registration.json()
    response = client.post(
        "/auth/login", headers=headers, json={"email": email, "password": password}
    )
    assert response.status_code == 200, "Live login failed"
    headers["X-CSRF-Token"] = response.json()["csrf_token"]
    campus = client.get("/campuses").json()["items"][0]
    graph_before = client.get(f"/campuses/{campus['id']}/graph").json()
    location = client.get("/locations", params={"campus_id": campus["id"]}).json()["items"][0]
    saved = client.post(
        "/me/saved-destinations", headers=headers, json={"location_id": location["id"]}
    )
    assert saved.status_code == 201
    subprocess.run([sys.executable, "scripts/dev.py", "stop"], cwd=ROOT, check=True)
    environment = dict(os.environ, DOCKER_CONFIG=str(ROOT / ".local/docker"))
    subprocess.run(["docker", "compose", "restart", "db"], cwd=ROOT, env=environment, check=True)
    subprocess.run(
        ["docker", "compose", "up", "-d", "--wait", "db"], cwd=ROOT, env=environment, check=True
    )
    subprocess.run([sys.executable, "scripts/dev.py", "start"], cwd=ROOT, check=True)
    assert client.get("/me").json()["id"] == account["id"], "User/session did not survive restart"
    assert client.get("/me/accessibility-profile").json()["unknown_policy"] == "exclude"
    assert client.get("/me/saved-destinations").json()["items"][0]["id"] == saved.json()["id"]
    graph_after = client.get(f"/campuses/{campus['id']}/graph").json()
    assert graph_before["features"] == graph_after["features"]
    assert graph_before["graph_version"] == graph_after["graph_version"]
    assert (
        client.delete("/me/saved-destinations/" + saved.json()["id"], headers=headers).status_code
        == 204
    )
    assert client.post("/auth/logout", headers=headers).status_code == 204
sys.path.insert(0, str(ROOT / "backend"))


def cleanup_account():
    from app.core.config import get_settings
    from app.models.entities import AuthSession, Profile, User

    key = uuid.UUID(account["id"])
    with (
        Session(create_engine(get_settings().database_url(), hide_parameters=True)) as db,
        db.begin(),
    ):
        db.execute(delete(AuthSession).where(AuthSession.user_id == key))
        db.execute(delete(Profile).where(Profile.user_id == key))
        db.execute(delete(User).where(User.id == key, User.normalized_email == email))


cleanup_account()
print(
    "PASS persistence H: user, session, profile, saved destination and graph survived API + DB restart; volume retained"
)
print("Temporary persistence account cleaned up; no password was logged.")
