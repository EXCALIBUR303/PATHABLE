import argparse
import getpass
import json
import sys
from pathlib import Path

import psycopg
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.models.entities import AdminAction, Profile, User
from app.schemas.requests import Register
from app.services.auth import hasher
from app.services.seed import seed_demo


def migrate():
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / "alembic.ini")), "head")


def prepare_database():
    settings = get_settings()
    kwargs = settings.database_url(owner=True, database="postgres").translate_connect_args(
        username="user", database="dbname"
    )
    with psycopg.connect(**kwargs, autocommit=True) as connection:
        found = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", (settings.postgres_db,)
        ).fetchone()
        if not found:
            connection.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(settings.postgres_db), sql.Identifier(settings.postgres_user)
                )
            )
        found = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (settings.app_db_user,)
        ).fetchone()
        if not found:
            connection.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(settings.app_db_user),
                    sql.Literal(settings.app_db_password.get_secret_value()),
                )
            )
    migrate()
    kwargs["dbname"] = settings.postgres_db
    with psycopg.connect(**kwargs) as connection:
        role = sql.Identifier(settings.app_db_user)
        connection.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
        connection.execute(
            sql.SQL(
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}"
            ).format(role)
        )
        for table in (
            "admin_actions",
            "graph_events",
            "report_status_events",
            "alembic_version",
            "spatial_ref_sys",
        ):
            connection.execute(
                sql.SQL("REVOKE UPDATE, DELETE ON {} FROM {}").format(sql.Identifier(table), role)
            )
        for table in ("alembic_version", "spatial_ref_sys"):
            connection.execute(
                sql.SQL("REVOKE INSERT ON {} FROM {}").format(sql.Identifier(table), role)
            )
        worker = sql.Identifier(settings.ml_worker_db_user)
        present = connection.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (settings.ml_worker_db_user,)
        ).fetchone()
        if not present:
            connection.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(worker))
        if settings.ml_worker_db_password is not None:
            connection.execute(
                sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                    worker, sql.Literal(settings.ml_worker_db_password.get_secret_value())
                )
            )
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(worker))
        connection.execute(
            sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(worker)
        )
        connection.execute(
            sql.SQL(
                "GRANT SELECT ON model_versions, report_evidence, inference_jobs, predictions TO {}"
            ).format(worker)
        )
        connection.execute(sql.SQL("GRANT UPDATE ON inference_jobs TO {}").format(worker))
        connection.execute(sql.SQL("GRANT INSERT ON predictions TO {}").format(worker))
        connection.execute(
            sql.SQL("REVOKE INSERT, UPDATE, DELETE ON model_versions FROM {}").format(role)
        )
        connection.execute(
            sql.SQL("REVOKE DELETE ON inference_jobs, predictions FROM {}").format(role)
        )
    print("Database migrated and restricted application/ML worker roles configured")


def main():
    parser = argparse.ArgumentParser(description="PathAble development administration")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("prepare-db")
    sub.add_parser("migrate")
    sub.add_parser("maintenance")
    model = sub.add_parser("register-model")
    model.add_argument("--bundle", required=True)
    model.add_argument("--activate", action="store_true")
    seed = sub.add_parser("seed")
    seed.add_argument("--synthetic", action="store_true", required=True)
    seed.add_argument("--if-empty", action="store_true")
    admin = sub.add_parser("create-admin")
    admin.add_argument("--email", required=True)
    admin.add_argument("--name", required=True)
    export = sub.add_parser("export-openapi")
    export.add_argument("--output", default="../docs/openapi.json")
    args = parser.parse_args()
    if args.action == "prepare-db":
        prepare_database()
    elif args.action == "migrate":
        migrate()
    elif args.action == "maintenance":
        from app.services.maintenance import maintain

        print(json.dumps(maintain(), sort_keys=True))
    elif args.action == "register-model":
        from app.services.ml_assets import register

        owner = create_engine(get_settings().database_url(owner=True), hide_parameters=True)
        with Session(owner) as db, db.begin():
            row = register(db, args.bundle, activate=args.activate)
            print("Registered immutable evaluated model", row.id, "enabled", row.enabled)
        owner.dispose()
    elif args.action == "export-openapi":
        from app.main import app

        Path(args.output).write_text(json.dumps(app.openapi(), indent=2) + "\n")
        print("OpenAPI exported")
    else:
        engine = create_engine(get_settings().database_url(), hide_parameters=True)
        with Session(engine) as db, db.begin():
            if args.action == "seed":
                print(seed_demo(db, if_empty=args.if_empty))
            elif args.action == "create-admin":
                if not sys.stdin.isatty():
                    raise SystemExit(
                        "Admin bootstrap requires an interactive terminal for secure password entry"
                    )
                password = getpass.getpass("New administrator password: ")
                if password != getpass.getpass("Repeat password: "):
                    raise SystemExit("Passwords do not match")
                data = Register(email=args.email, display_name=args.name, password=password)
                if db.scalar(select(User).where(User.normalized_email == str(data.email).lower())):
                    raise SystemExit("Account already exists; refusing implicit role promotion")
                user = User(
                    normalized_email=str(data.email).lower(),
                    display_name=data.display_name,
                    password_hash=hasher.hash(data.password),
                    role="admin",
                )
                db.add(user)
                db.flush()
                db.add(Profile(user_id=user.id))
                db.add(
                    AdminAction(
                        actor_id=user.id,
                        action_type="admin_bootstrap",
                        resource_type="users",
                        resource_id=user.id,
                        before_json={},
                        after_json={"role": "admin"},
                        reason="Explicit local administrator bootstrap",
                        request_id="cli:admin-bootstrap",
                        graph_version=None,
                    )
                )
                print("Administrator created; password not logged")


if __name__ == "__main__":
    main()
