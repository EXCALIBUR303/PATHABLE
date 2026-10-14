from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", extra="ignore", hide_input_in_errors=True
    )
    app_env: Literal["development", "test", "production"] = "development"
    app_origin: str = "http://localhost:5173"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "pathable"
    postgres_user: str = "pathable_owner"
    postgres_password: SecretStr | None = None
    app_db_user: str = "pathable_app"
    app_db_password: SecretStr
    csrf_secret: SecretStr
    rate_limit_hash_key: SecretStr
    session_cookie_secure: bool = False
    upload_root: Path = ROOT / ".local/uploads"
    upload_user_quota_bytes: int = 100 * 1024 * 1024

    ml_enabled: bool = False
    ml_asset_root: Path = ROOT / ".local/ml-models"
    ml_python: Path = ROOT / ".local/ml-venv/bin/python"
    ml_worker_db_user: str = "pathable_ml_worker"
    ml_worker_db_password: SecretStr | None = None

    @property
    def private_ml_root(self):
        return self.ml_asset_root if self.ml_asset_root.is_absolute() else ROOT / self.ml_asset_root

    def worker_database_url(self):
        if self.ml_worker_db_password is None:
            raise ValueError("ML worker database credential is not configured")
        return self.database_url().set(
            username=self.ml_worker_db_user, password=self.ml_worker_db_password.get_secret_value()
        )

    @property
    def private_upload_root(self):
        return self.upload_root if self.upload_root.is_absolute() else ROOT / self.upload_root

    @model_validator(mode="after")
    def secure_configuration(self):
        if len({self.postgres_user, self.app_db_user, self.ml_worker_db_user}) != 3:
            raise ValueError("Owner, application and ML worker database roles must be distinct")
        origin = urlsplit(self.app_origin)
        if (
            origin.scheme not in ("http", "https")
            or not origin.hostname
            or origin.path
            or origin.query
            or origin.fragment
            or origin.username
        ):
            raise ValueError(
                "APP_ORIGIN must be an exact HTTP(S) origin without path or credentials"
            )
        for field in ("postgres_password", "app_db_password", "csrf_secret", "rate_limit_hash_key"):
            value = getattr(self, field)
            if value is not None and len(value.get_secret_value()) < 24:
                raise ValueError(f"{field} must contain at least 24 characters")
        if self.app_env == "production" and (
            not self.session_cookie_secure or not self.app_origin.startswith("https://")
        ):
            raise ValueError("Production requires HTTPS origin and secure cookies")
        return self

    @property
    def cookie_name(self):
        return "__Host-pathable_session" if self.session_cookie_secure else "pathable_session"

    def database_url(self, *, owner=False, database=None):
        password = self.postgres_password if owner else self.app_db_password
        if password is None:
            raise ValueError("Owner database credential is not configured for this process")
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user if owner else self.app_db_user,
            password=password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=database or self.postgres_db,
        )


@lru_cache
def get_settings():
    return Settings()
