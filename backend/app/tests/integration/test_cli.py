import sys

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.db.session import engine
from app.models.entities import AdminAction, Profile, User
from app.tests.conftest import PASSWORD, login


def test_secure_admin_bootstrap(monkeypatch, capsys, client):
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.cli", "create-admin", "--email", "bootstrap@example.com", "--name", "Local admin"],
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: PASSWORD)
    cli.main()
    assert PASSWORD not in capsys.readouterr().out
    with Session(engine()) as db:
        user = db.scalar(select(User).where(User.normalized_email == "bootstrap@example.com"))
        assert user.role == "admin"
        assert db.scalar(select(Profile).where(Profile.user_id == user.id))
        assert (
            db.scalar(select(AdminAction).where(AdminAction.actor_id == user.id)).action_type
            == "admin_bootstrap"
        )
    login(client, "bootstrap@example.com")
    assert client.get("/api/v1/me").json()["role"] == "admin"
    with pytest.raises(SystemExit, match="refusing implicit role promotion"):
        cli.main()


def test_admin_bootstrap_refuses_noninteractive_password(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["app.cli", "create-admin", "--email", "bootstrap@example.com", "--name", "Local admin"],
    )
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    with pytest.raises(SystemExit, match="interactive terminal"):
        cli.main()
    with Session(engine()) as db:
        assert (
            db.scalar(select(User).where(User.normalized_email == "bootstrap@example.com")) is None
        )
