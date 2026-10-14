from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Problem
from app.db.session import get_db
from app.models.entities import (
    Campus,
    Infrastructure,
    InfrastructureEdge,
    Location,
    PathEdge,
    PathNode,
    Profile,
    SavedDestination,
    User,
)
from app.models.reporting import EdgeRestriction
from app.repositories.views import enrich, page, public_user, record
from app.schemas import requests as inputs
from app.schemas import responses as outputs
from app.schemas.routing import RouteFound, RouteNoRoute, RouteRequest
from app.services import auth, graph

router = APIRouter(
    prefix="/api/v1",
    responses={
        status: {
            "model": outputs.ProblemOut,
            "content": {
                "application/problem+json": {"schema": outputs.ProblemOut.model_json_schema()}
            },
        }
        for status in (400, 401, 403, 404, 409, 413, 415, 422, 429, 500, 503)
    },
)
DB = Annotated[Session, Depends(get_db, scope="function")]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/health/live")
def live():
    return {"status": "alive"}


@router.get("/health/ready")
def ready(db: DB):
    version = db.scalar(text("SELECT version_num FROM alembic_version"))
    db.scalar(text("SELECT PostGIS_Version()"))
    if version != "0003_ml":
        raise Problem(503, "MIGRATION_REQUIRED", "Database migration is not current")
    return {"status": "ready"}


@router.get("/auth/session", response_model=outputs.SessionOut)
def session_view(request: Request, response: Response, db: DB):
    session, user, token = auth.current_session(request, db, required=False)
    if not session:
        auth.rate_limit("session", auth.client_identifier(request), 20)
        session, token = auth.issue_session(db, response)
    return {
        "user": public_user(user) if user else None,
        "csrf_token": auth.csrf_token(token),
        "expires_at": session.expires_at,
    }


@router.post("/auth/register", status_code=201, response_model=outputs.UserOut)
def register(payload: inputs.Register, request: Request, db: DB):
    auth.require_csrf(request, db)
    auth.rate_limit("registration", auth.client_identifier(request), 10, 3600)
    user = User(
        normalized_email=str(payload.email).lower(),
        display_name=payload.display_name,
        password_hash=auth.hasher.hash(payload.password),
        role="user",
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    return public_user(user)


@router.post("/auth/login", response_model=outputs.SessionOut)
def login(payload: inputs.Credentials, request: Request, response: Response, db: DB):
    previous, _ = auth.require_csrf(request, db)
    ip = auth.client_identifier(request)
    email = str(payload.email).lower()
    for identity in (ip, email):
        auth.rate_limit("login_minute", identity, 5)
        auth.rate_limit("login_hour", identity, 30, 3600)
    user = db.scalar(select(User).where(User.normalized_email == email))
    valid = auth.verify_password(user.password_hash if user else auth.DUMMY_HASH, payload.password)
    if not valid or not user or not user.active:
        raise Problem(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    previous.revoked_at = db.scalar(select(func.clock_timestamp()))
    if auth.hasher.check_needs_rehash(user.password_hash):
        user.password_hash = auth.hasher.hash(payload.password)
    session, token = auth.issue_session(db, response, user)
    return {
        "user": public_user(user),
        "csrf_token": auth.csrf_token(token),
        "expires_at": session.expires_at,
    }


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    auth.require_origin(request)
    session, _, _ = auth.current_session(request, db, required=False)
    if session:
        auth.require_csrf(request, db)
        session.revoked_at = db.scalar(select(func.clock_timestamp()))
    response.delete_cookie(
        get_settings().cookie_name,
        path="/",
        secure=get_settings().session_cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=outputs.UserOut)
def me(request: Request, db: DB):
    return public_user(auth.require_user(request, db))


@router.patch("/me", response_model=outputs.UserOut)
def edit_me(payload: inputs.EditUser, request: Request, db: DB):
    user = auth.require_user(request, db)
    user = graph.require_row(db, User, user.id, lock=True)
    graph.expect_version(user, payload.expected_version)
    user.display_name = payload.display_name
    user.row_version += 1
    return public_user(user)


@router.get("/me/accessibility-profile", response_model=outputs.ProfileOut)
def profile(request: Request, db: DB):
    user = auth.require_user(request, db)
    return db.scalar(select(Profile).where(Profile.user_id == user.id))


@router.put("/me/accessibility-profile", response_model=outputs.ProfileOut)
def edit_profile(payload: inputs.ProfileInput, request: Request, db: DB):
    user = auth.require_user(request, db)
    row = db.scalar(select(Profile).where(Profile.user_id == user.id).with_for_update())
    graph.expect_version(row, payload.expected_version)
    for key, value in payload.model_dump(exclude={"expected_version"}).items():
        setattr(row, key, sorted(set(value)) if key == "excluded_surfaces" else value)
    row.row_version += 1
    db.flush()
    return row


@router.get("/me/saved-destinations", response_model=outputs.Page[outputs.SavedOut])
def saved(request: Request, db: DB, limit: Limit = 25, cursor: str | None = None):
    user = auth.require_user(request, db)
    rows, cursor = page(
        db,
        select(SavedDestination).where(SavedDestination.user_id == user.id),
        SavedDestination,
        limit,
        cursor,
        "saved:" + str(user.id),
    )
    return {"items": rows, "next_cursor": cursor}


@router.post("/me/saved-destinations", status_code=201, response_model=outputs.SavedOut)
def save_destination(payload: inputs.SaveDestination, request: Request, db: DB):
    user = auth.require_user(request, db)
    location = graph.require_row(db, Location, payload.location_id)
    if not location.active:
        raise Problem(422, "INACTIVE_LOCATION", "Location is retired")
    row = SavedDestination(
        user_id=user.id,
        campus_id=location.campus_id,
        location_id=location.id,
        label=payload.label or location.name,
    )
    db.add(row)
    db.flush()
    return row


@router.delete("/me/saved-destinations/{key}", status_code=204)
def unsave_destination(key: UUID, request: Request, db: DB):
    user = auth.require_user(request, db)
    result = db.execute(
        delete(SavedDestination).where(
            SavedDestination.id == key, SavedDestination.user_id == user.id
        )
    )
    if not result.rowcount:
        raise Problem(404, "NOT_FOUND", "Saved destination not found")


@router.get("/campuses", response_model=outputs.Page[outputs.CampusOut])
def campuses(db: DB, limit: Limit = 25, cursor: str | None = None):
    rows, cursor = page(db, select(Campus), Campus, limit, cursor, "campuses")
    return {"items": rows, "next_cursor": cursor}


@router.get("/locations", response_model=outputs.Page[outputs.LocationOut])
def locations(
    campus_id: UUID,
    db: DB,
    q: Annotated[str, Query(max_length=100)] = "",
    limit: Limit = 25,
    cursor: str | None = None,
):
    statement = select(Location).where(Location.campus_id == campus_id, Location.active)
    if q:
        statement = statement.where(Location.name.icontains(q, autoescape=True))
    rows, cursor = page(db, statement, Location, limit, cursor, f"locations:{campus_id}:{q}")
    return {"items": enrich(db, rows, "location"), "next_cursor": cursor}


@router.get("/locations/{key}", response_model=outputs.LocationOut)
def location(key: UUID, db: DB):
    return enrich(db, [graph.require_row(db, Location, key)], "location")[0]


@router.get("/infrastructure", response_model=outputs.Page[outputs.InfrastructureOut])
def infrastructure(
    campus_id: UUID, db: DB, bbox: str | None = None, limit: Limit = 25, cursor: str | None = None
):
    graph.expire_observations(db, campus_id)
    statement = select(Infrastructure).where(
        Infrastructure.campus_id == campus_id, Infrastructure.active
    )
    if bbox:
        try:
            west, south, east, north = map(float, bbox.split(","))
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise ValueError
        except ValueError:
            raise Problem(422, "INVALID_BBOX", "Use west,south,east,north WGS84 bounds") from None
        statement = statement.where(
            func.ST_Intersects(
                Infrastructure.point, func.ST_MakeEnvelope(west, south, east, north, 4326)
            )
        )
    rows, cursor = page(
        db, statement, Infrastructure, limit, cursor, f"infrastructure:{campus_id}:{bbox}"
    )
    return {"items": enrich(db, rows, "infrastructure"), "next_cursor": cursor}


@router.get("/infrastructure/{key}", response_model=outputs.InfrastructureOut)
def infrastructure_detail(key: UUID, db: DB):
    row = graph.require_row(db, Infrastructure, key)
    graph.expire_observations(db, row.campus_id)
    return enrich(db, [row], "infrastructure")[0]


def graph_metadata(db, campus_id):
    campus = graph.require_row(db, Campus, campus_id)
    state = graph.expire_observations(db, campus_id)
    return {
        "graph_version": str(state.version),
        "validated_at": db.scalar(select(func.clock_timestamp())),
        "valid_until": state.next_expiry_at,
        "data_origin": campus.data_origin,
        "cost_model_version": state.cost_model_version,
        "policy_version": state.policy_version,
    }


@router.get("/campuses/{campus_id}/graph-version", response_model=outputs.VersionOut)
def graph_version(campus_id: UUID, db: DB):
    return graph_metadata(db, campus_id)


@router.get("/campuses/{campus_id}/graph", response_model=outputs.GraphOut)
def graph_view(campus_id: UUID, db: DB):
    metadata = graph_metadata(db, campus_id)
    restrictions = {
        edge_id: (count, closed)
        for edge_id, count, closed in db.execute(
            select(
                EdgeRestriction.edge_id,
                func.count(),
                func.bool_or(EdgeRestriction.kind == "closed"),
            )
            .where(EdgeRestriction.campus_id == campus_id, EdgeRestriction.released_at.is_(None))
            .group_by(EdgeRestriction.edge_id)
        )
    }
    dependencies = {
        edge_id: (closed, blocked)
        for edge_id, closed, blocked in db.execute(
            select(
                InfrastructureEdge.edge_id,
                func.bool_or((~Infrastructure.active) | (Infrastructure.availability == "closed")),
                func.bool_or(Infrastructure.availability == "temporarily_blocked"),
            )
            .join(Infrastructure, Infrastructure.id == InfrastructureEdge.infrastructure_id)
            .where(InfrastructureEdge.campus_id == campus_id)
            .group_by(InfrastructureEdge.edge_id)
        )
    }
    features = []
    for model, field in ((PathNode, "point"), (PathEdge, "geometry")):
        rows = list(
            db.scalars(
                select(model)
                .where(model.campus_id == campus_id, model.active)
                .order_by(model.id)
                .limit(10001)
            )
        )
        if len(rows) > 10000:
            raise Problem(413, "GRAPH_TOO_LARGE", "Campus graph exceeds inline export limit")
        for row in rows:
            properties = record(row)
            if model is PathEdge:
                count, closed = restrictions.get(row.id, (0, False))
                dependency_closed, dependency_blocked = dependencies.get(row.id, (False, False))
                properties["active_restriction_count"] = count
                properties["effective_availability"] = (
                    "closed"
                    if row.availability == "closed" or closed or dependency_closed
                    else "temporarily_blocked"
                    if row.availability == "temporarily_blocked" or count or dependency_blocked
                    else "open"
                )
            features.append(
                {
                    "type": "Feature",
                    "id": row.id,
                    "geometry": properties[field],
                    "properties": properties,
                }
            )
    return {"type": "FeatureCollection", "features": features, **metadata}


@router.post("/routes/calculate", response_model=RouteFound | RouteNoRoute)
def calculate_route(payload: RouteRequest, request: Request, db: DB):
    from app.services.routing import route_response

    _, user, _ = auth.current_session(request, db, required=False)
    identity = str(user.id) if user else auth.client_identifier(request)
    # Release the optional-auth connection before the independent rate/snapshot sessions.
    # Otherwise concurrent callers can hold the entire pool while each needs a second slot.
    db.commit()
    auth.rate_limit("route", identity, 60)
    # A read-only public calculation does not require an anonymous auth session/CSRF.
    # Its graph transactions are independent of the request's authentication read.
    return route_response(payload)


def admin_edit(resource, payload, request, db, key=None, retire=False):
    actor = auth.require_user(request, db, admin=True)
    row = graph.edit_resource(db, resource, payload, actor, request.state.request_id, key, retire)
    if resource in ("locations", "infrastructure"):
        return enrich(db, [row], "location" if resource == "locations" else "infrastructure")[0]
    return record(row)


@router.post("/admin/locations", status_code=201, response_model=outputs.LocationOut)
def create_location(payload: inputs.LocationCreate, request: Request, db: DB):
    return admin_edit("locations", payload, request, db)


@router.patch("/admin/locations/{key}", response_model=outputs.LocationOut)
def patch_location(key: UUID, payload: inputs.LocationEdit, request: Request, db: DB):
    return admin_edit("locations", payload, request, db, key)


@router.post("/admin/path-nodes", status_code=201, response_model=outputs.NodeOut)
def create_node(payload: inputs.NodeCreate, request: Request, db: DB):
    return admin_edit("path-nodes", payload, request, db)


@router.patch("/admin/path-nodes/{key}", response_model=outputs.NodeOut)
def patch_node(key: UUID, payload: inputs.NodeEdit, request: Request, db: DB):
    return admin_edit("path-nodes", payload, request, db, key)


@router.post("/admin/path-edges", status_code=201, response_model=outputs.EdgeOut)
def create_edge(payload: inputs.EdgeCreate, request: Request, db: DB):
    return admin_edit("path-edges", payload, request, db)


@router.patch("/admin/path-edges/{key}", response_model=outputs.EdgeOut)
def patch_edge(key: UUID, payload: inputs.EdgeEdit, request: Request, db: DB):
    return admin_edit("path-edges", payload, request, db, key)


@router.post("/admin/path-edges/{key}/retire", response_model=outputs.EdgeOut)
def retire_edge(key: UUID, payload: inputs.AdminEdit, request: Request, db: DB):
    return admin_edit("path-edges", payload, request, db, key, retire=True)


@router.post("/admin/infrastructure", status_code=201, response_model=outputs.InfrastructureOut)
def create_infrastructure(payload: inputs.InfrastructureCreate, request: Request, db: DB):
    return admin_edit("infrastructure", payload, request, db)


@router.patch("/admin/infrastructure/{key}", response_model=outputs.InfrastructureOut)
def patch_infrastructure(key: UUID, payload: inputs.InfrastructureEdit, request: Request, db: DB):
    return admin_edit("infrastructure", payload, request, db, key)
