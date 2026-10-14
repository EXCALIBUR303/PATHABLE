import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Problem
from app.db.session import engine
from app.models.entities import AuthSession, RateBucket, User

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token):
    key = get_settings().csrf_secret.get_secret_value().encode()
    return (
        base64.urlsafe_b64encode(hmac.digest(key, ("csrf-v1:" + token).encode(), "sha256"))
        .decode()
        .rstrip("=")
    )


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def clock_now(db):
    return db.scalar(select(func.clock_timestamp()))


def rate_limit(scope, identifier, limit, seconds=60):
    """Separate committed transaction: failed authentication must still consume quota."""
    key = get_settings().rate_limit_hash_key.get_secret_value().encode()
    digest = hmac.new(key, identifier.encode(), hashlib.sha256).hexdigest()
    with Session(engine()) as db, db.begin():
        now = clock_now(db)
        bucket = int(now.timestamp()) // seconds * seconds
        db.execute(text("SELECT pg_advisory_xact_lock(9171042)"))
        db.execute(delete(RateBucket).where(RateBucket.expires_at < now))
        total = db.scalar(select(func.count()).select_from(RateBucket))
        if total >= 100000:
            raise Problem(
                503, "RATE_LIMIT_CAPACITY", "Authentication capacity temporarily unavailable"
            )
        statement = insert(RateBucket).values(
            scope=scope,
            identifier_hash=digest,
            bucket_start=bucket,
            count=1,
            expires_at=now + timedelta(seconds=seconds),
        )
        count = db.scalar(
            statement.on_conflict_do_update(
                index_elements=[
                    RateBucket.scope,
                    RateBucket.identifier_hash,
                    RateBucket.bucket_start,
                ],
                set_={"count": RateBucket.count + 1},
            ).returning(RateBucket.count)
        )
    if count > limit:
        raise Problem(
            429,
            "RATE_LIMITED",
            "Too many requests; retry later",
            retry_after=max(1, seconds - (int(now.timestamp()) - bucket)),
        )


def client_identifier(request):
    # Ignore attacker-controlled forwarding headers; trusted proxy integration is a release gate.
    return request.client.host if request.client else "unknown"


def require_origin(request):
    if request.headers.get("origin") != get_settings().app_origin:
        raise Problem(403, "CSRF_ORIGIN", "Request origin is not allowed")


def current_session(request, db, *, required=True):
    token = request.cookies.get(get_settings().cookie_name, "")
    session = None
    user = None
    if 20 <= len(token) <= 200:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(token)))
    now = db.scalar(select(func.clock_timestamp()))
    if session:
        if (
            session.revoked_at
            or session.expires_at <= now
            or session.last_seen_at + timedelta(hours=24) <= now
        ):
            session = None
        elif session.user_id:
            user = db.get(User, session.user_id)
            if not user or not user.active or user.auth_version != session.issued_auth_version:
                session = None
                user = None
    if not session and required:
        raise Problem(401, "AUTHENTICATION_REQUIRED", "A valid session is required")
    if session:
        session.last_seen_at = now
    return session, user, token


def require_csrf(request, db):
    require_origin(request)
    session, user, token = current_session(request, db)
    received = request.headers.get("x-csrf-token", "")
    if not received.isascii() or not hmac.compare_digest(received, csrf_token(token)):
        raise Problem(403, "CSRF_INVALID", "Refresh the session and retry with a valid CSRF token")
    return session, user


def require_user(request, db, *, admin=False):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        _, user = require_csrf(request, db)
    else:
        _, user, _ = current_session(request, db)
    if not user:
        raise Problem(401, "AUTHENTICATION_REQUIRED", "Sign in to continue")
    if admin and user.role != "admin":
        raise Problem(403, "ADMIN_REQUIRED", "Administrator access is required")
    return user


def issue_session(db, response: Response, user=None):
    now = db.scalar(select(func.clock_timestamp()))
    # Expired sessions are cleaned during issuance; scheduled maintenance is later operations work.
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        token_hash=hash_token(token),
        user_id=user.id if user else None,
        issued_auth_version=user.auth_version if user else None,
        expires_at=now + (timedelta(days=7) if user else timedelta(minutes=30)),
        last_seen_at=now,
    )
    db.add(session)
    response.set_cookie(
        get_settings().cookie_name,
        token,
        httponly=True,
        secure=get_settings().session_cookie_secure,
        samesite="lax",
        path="/",
        max_age=7 * 86400 if user else 1800,
    )
    return session, token


def current_actor(db, actor, *, admin=False, exclusive=False):
    """Refresh authorization under a transaction lock, exclusive for quota reservations."""
    expected_auth_version = actor.auth_version
    row = db.scalar(
        select(User)
        .where(User.id == actor.id)
        .with_for_update(read=not exclusive)
        .execution_options(populate_existing=True)
    )
    if row is None or not row.active or row.auth_version != expected_auth_version:
        raise Problem(
            401, "AUTHENTICATION_REQUIRED", "Account authorization changed; sign in again"
        )
    if admin and row.role != "admin":
        raise Problem(403, "ADMIN_REQUIRED", "Administrator access is required")
    return row
