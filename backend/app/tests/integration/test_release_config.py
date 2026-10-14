import pytest
from pydantic import ValidationError

from app.core.config import Settings


def configuration(**changes):
    return Settings(
        _env_file=None,
        app_env="production",
        app_origin="https://localhost:8443",
        session_cookie_secure=True,
        app_db_password="a" * 32,
        csrf_secret="b" * 32,
        rate_limit_hash_key="c" * 32,
        **changes,
    )


def test_runtime_needs_no_owner_credential(monkeypatch):
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    value = configuration(postgres_password=None)
    assert value.cookie_name == "__Host-pathable_session"
    assert value.database_url().username == value.app_db_user
    with pytest.raises(ValueError, match="Owner database credential"):
        value.database_url(owner=True)


def test_optional_owner_credential_still_rejects_weak_values():
    with pytest.raises(ValidationError):
        configuration(postgres_password="weak")


@pytest.mark.parametrize(
    "first,second",
    [
        ("postgres_user", "app_db_user"),
        ("postgres_user", "ml_worker_db_user"),
        ("app_db_user", "ml_worker_db_user"),
    ],
)
def test_database_role_boundaries_cannot_collapse(first, second):
    roles = {
        "postgres_user": "audit_owner",
        "app_db_user": "audit_app",
        "ml_worker_db_user": "audit_worker",
    }
    roles[second] = roles[first]
    with pytest.raises(ValidationError, match="roles must be distinct"):
        configuration(**roles)
