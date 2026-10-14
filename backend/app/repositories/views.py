import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select

from app.core.errors import Problem
from app.models.entities import AccessPoint, InfrastructureEdge


def public_user(row):
    return {
        "id": row.id,
        "email": row.normalized_email,
        "display_name": row.display_name,
        "role": row.role,
        "row_version": row.row_version,
    }


def record(row):
    """Explicitly public resources only: never call this on a User or AuthSession."""
    value = {
        c.name: getattr(row, c.name)
        for c in row.__table__.columns
        if c.name not in ("point", "geometry", "boundary")
    }
    if hasattr(row, "point_json"):
        value["point"] = json.loads(row.point_json)
    if hasattr(row, "geometry_json"):
        value["geometry"] = json.loads(row.geometry_json)
    # Public provenance identifies time/source, not the administrator's account.
    value.pop("verified_by", None)
    return value


def enrich(db, rows, kind):
    ids = [row.id for row in rows]
    mapping = {key: [] for key in ids}
    if kind == "location":
        for point in db.scalars(select(AccessPoint).where(AccessPoint.location_id.in_(ids))):
            mapping[point.location_id].append(
                {
                    "node_id": point.node_id,
                    "label": point.label,
                    "kind": point.kind,
                    "is_primary": point.is_primary,
                }
            )
        field = "access_points"
    else:
        for link in db.scalars(
            select(InfrastructureEdge).where(InfrastructureEdge.infrastructure_id.in_(ids))
        ):
            mapping[link.infrastructure_id].append(link.edge_id)
        field = "edge_ids"
    return [{**record(row), field: mapping[row.id]} for row in rows]


def page(db, statement, model, limit, cursor, scope):
    if cursor:
        try:
            if len(cursor) > 1000:
                raise ValueError
            data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            if not isinstance(data, dict) or any(
                not isinstance(data.get(field), str) for field in ("time", "scope", "id")
            ):
                raise ValueError
            timestamp = datetime.fromisoformat(data["time"])
            if data["scope"] != scope or not timestamp.tzinfo:
                raise ValueError
            key = UUID(data["id"])
        except (ValueError, KeyError, TypeError, UnicodeDecodeError):
            raise Problem(400, "INVALID_CURSOR", "Cursor is invalid for this query") from None
        statement = statement.where(
            or_(model.created_at > timestamp, and_(model.created_at == timestamp, model.id > key))
        )
    rows = list(db.scalars(statement.order_by(model.created_at, model.id).limit(limit + 1)))
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1]
        next_cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {"time": last.created_at.isoformat(), "id": str(last.id), "scope": scope}
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
    return rows[:limit], next_cursor
