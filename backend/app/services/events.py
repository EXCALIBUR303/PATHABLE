"""Durable per-campus replay with short DB transactions and expiring stream leases."""

import hashlib
import hmac
import json
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Problem
from app.db.session import engine
from app.models.entities import Campus, GraphEvent, GraphState
from app.models.reporting import SSELease
from app.services.graph import expire_observations

RETENTION = timedelta(days=7)
LEASE_TTL = timedelta(seconds=45)


def claim_stream(identity):
    digest = hmac.new(
        get_settings().rate_limit_hash_key.get_secret_value().encode(),
        identity.encode(),
        hashlib.sha256,
    ).hexdigest()
    with Session(engine()) as db, db.begin():
        # A brief global lease lock bounds admission across API processes.
        db.execute(select(func.pg_advisory_xact_lock(9171043)))
        now = db.scalar(select(func.clock_timestamp()))
        db.execute(delete(SSELease).where(SSELease.expires_at <= now))
        count = db.scalar(
            select(func.count()).select_from(SSELease).where(SSELease.identifier_hash == digest)
        )
        if count >= 3:
            raise Problem(
                429, "STREAM_LIMIT", "At most three live graph streams are allowed per client"
            )
        if db.scalar(select(func.count()).select_from(SSELease)) >= 200:
            raise Problem(503, "STREAM_CAPACITY", "Live update capacity is temporarily full")
        identity = uuid4()
        db.add(SSELease(id=identity, identifier_hash=digest, expires_at=now + LEASE_TTL))
        return identity


def release_stream(identity):
    with Session(engine()) as db, db.begin():
        db.execute(delete(SSELease).where(SSELease.id == identity))


def event_batch(campus_id, cursor, lease=None, *, trusted=False):
    with Session(engine()) as db, db.begin():
        campus = db.get(Campus, campus_id)
        if campus is None:
            raise Problem(404, "NOT_FOUND", "Campus not found")
        if db.get(GraphState, campus_id) is None:
            raise Problem(503, "GRAPH_INVALID", "Campus graph metadata is missing")
        state = expire_observations(db, campus_id)
        now = db.scalar(select(func.clock_timestamp()))
        if lease is not None:
            row = db.get(SSELease, lease)
            if row is None or row.expires_at <= now:
                raise Problem(503, "STREAM_EXPIRED", "Live update lease expired; reconnect")
            row.expires_at = now + LEASE_TTL
        valid = False
        if (
            cursor is not None
            and str(cursor).isascii()
            and str(cursor).isdigit()
            and len(str(cursor)) <= 19
        ):
            value = int(cursor)
            if 0 < value <= state.version:
                retained = db.get(GraphEvent, (campus_id, value))
                valid = trusted or (
                    retained is not None and retained.occurred_at >= now - RETENTION
                )
        if not valid:
            return [
                {
                    "event": "graph.reset",
                    "id": str(state.version),
                    "data": {
                        "campus_id": str(campus_id),
                        "graph_version": str(state.version),
                        "changed_edge_ids": [],
                        "changes_truncated": False,
                        "reason": "initial_connection" if cursor is None else "cursor_reset",
                        "occurred_at": now.isoformat(),
                    },
                }
            ]
        rows = list(
            db.scalars(
                select(GraphEvent)
                .where(
                    GraphEvent.campus_id == campus_id,
                    GraphEvent.graph_version > value,
                    GraphEvent.occurred_at >= now - RETENTION,
                )
                .order_by(GraphEvent.graph_version)
                .limit(100)
            )
        )
        if (rows and rows[0].graph_version != value + 1) or (not rows and value != state.version):
            return [
                {
                    "event": "graph.reset",
                    "id": str(state.version),
                    "data": {
                        "campus_id": str(campus_id),
                        "graph_version": str(state.version),
                        "changed_edge_ids": [],
                        "changes_truncated": False,
                        "reason": "replay_gap",
                        "occurred_at": now.isoformat(),
                    },
                }
            ]
        # Missing internal versions also force a reset rather than a partial replay.
        if any(row.graph_version != value + i + 1 for i, row in enumerate(rows)):
            return [
                {
                    "event": "graph.reset",
                    "id": str(state.version),
                    "data": {
                        "campus_id": str(campus_id),
                        "graph_version": str(state.version),
                        "changed_edge_ids": [],
                        "changes_truncated": False,
                        "reason": "replay_gap",
                        "occurred_at": now.isoformat(),
                    },
                }
            ]
        return [
            {
                "event": row.event_type,
                "id": str(row.graph_version),
                "data": {
                    "campus_id": str(row.campus_id),
                    "graph_version": str(row.graph_version),
                    "changed_edge_ids": [str(edge) for edge in row.changed_edge_ids[:200]],
                    "changes_truncated": len(row.changed_edge_ids) > 200,
                    "reason": row.reason,
                    "occurred_at": row.occurred_at.isoformat(),
                },
            }
            for row in rows
        ]


def encode_event(event):
    return f"id: {event['id']}\nevent: {event['event']}\ndata: {json.dumps(event['data'], separators=(',', ':'))}\n\n"
