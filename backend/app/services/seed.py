import secrets
import uuid
from datetime import timedelta

from sqlalchemy import func, select

from app.models.entities import (
    AccessPoint,
    Campus,
    GraphEvent,
    GraphState,
    Infrastructure,
    InfrastructureEdge,
    Location,
    PathEdge,
    PathNode,
    User,
)
from app.services.auth import hasher
from app.services.graph import geometry


def demo_id(name):
    return uuid.uuid5(uuid.NAMESPACE_URL, "pathable:demo:v1:" + name)


POSITIONS = {
    "s": [0, 0],
    "a": [0.0001, 0],
    "t": [0.0002, 0],
    "b": [0, 0.0001],
    "c": [0.0002, 0.0001],
    "d": [0.0001, -0.0002],
    "u": [0.0003, 0],
    "n": [0, 0.0003],
    "v": [0.0002, 0.0003],
}
EDGES = [
    ("stairs-west", "s", "a", {"has_stairs": True}),
    ("stairs-east", "a", "t", {"has_stairs": True}),
    ("upper-west", "s", "b", {}),
    ("ramp-cross", "b", "c", {"slope_pct": 4, "has_ramp": True}),
    ("upper-east", "c", "t", {}),
    ("lower-west", "s", "d", {}),
    ("lower-east", "d", "t", {}),
    (
        "unknown-direct",
        "s",
        "t",
        {
            "verification": "unverified",
            "accessibility": "unknown",
            "width_m": None,
            "slope_pct": None,
            "has_stairs": None,
            "surface": "unknown",
        },
    ),
    ("gravel-west", "s", "u", {"surface": "gravel"}),
    ("gravel-east", "u", "t", {"surface": "uneven"}),
    ("steep-north", "b", "n", {"slope_pct": 12}),
    ("narrow-north", "n", "v", {"width_m": 0.6}),
    ("blocked-north", "v", "c", {"availability": "temporarily_blocked"}),
]


def seed_demo(db, *, if_empty=False):
    campus_id = demo_id("campus")
    existing = db.get(Campus, campus_id)
    if existing:
        if if_empty:
            return "Existing synthetic campus preserved"
        expected = {
            PathNode: [demo_id("node:" + name) for name in POSITIONS],
            PathEdge: [demo_id("edge:" + edge[0]) for edge in EDGES],
            Location: [demo_id("location:" + n) for n in ("s", "t", "b")],
            Infrastructure: [demo_id("infrastructure:ramp"), demo_id("infrastructure:entrance")],
        }
        for model, keys in expected.items():
            rows = list(db.scalars(select(model).where(model.id.in_(keys))))
            if len(rows) != len(keys) or any(row.row_version != 1 for row in rows):
                raise RuntimeError(
                    "Seed records have changed or are incomplete; refusing to overwrite"
                )
        return "Synthetic seed already present; no changes"
    now = db.scalar(select(func.clock_timestamp()))
    system_id = demo_id("verifier")
    db.add(
        User(
            id=system_id,
            normalized_email="synthetic-verifier@demo.invalid",
            display_name="Synthetic fixture verifier",
            password_hash=hasher.hash(secrets.token_urlsafe(40)),
            role="user",
            active=False,
        )
    )
    db.add(
        Campus(
            id=campus_id,
            name="PathAble Fictional Campus",
            data_origin="synthetic_demo",
            attribution="Fictional demonstration infrastructure; not Woxsen University survey data.",
            boundary=geometry(
                {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-0.001, -0.001],
                            [0.001, -0.001],
                            [0.001, 0.001],
                            [-0.001, 0.001],
                            [-0.001, -0.001],
                        ]
                    ],
                }
            ),
        )
    )
    db.flush()
    for name, coordinates in POSITIONS.items():
        db.add(
            PathNode(
                id=demo_id("node:" + name),
                campus_id=campus_id,
                name="Demo " + name,
                point=geometry({"type": "Point", "coordinates": coordinates}),
                level=0,
                active=True,
            )
        )
    db.flush()
    verified = {
        "verification": "verified",
        "verified_at": now,
        "verified_until": now + timedelta(days=30),
        "verified_by": system_id,
        "provenance": "synthetic_demo: authored fixture, not field observations",
    }
    for name, source, target, overrides in EDGES:
        values = {
            "width_m": 1.2,
            "slope_pct": 0,
            "surface": "smooth",
            "has_stairs": False,
            "has_ramp": False,
            "accessibility": "accessible",
            "availability": "open",
            **verified,
            **overrides,
        }
        if values["verification"] != "verified":
            values.update(verified_at=None, verified_until=None, verified_by=None)
        db.add(
            PathEdge(
                id=demo_id("edge:" + name),
                campus_id=campus_id,
                source_node_id=demo_id("node:" + source),
                target_node_id=demo_id("node:" + target),
                geometry=geometry(
                    {"type": "LineString", "coordinates": [POSITIONS[source], POSITIONS[target]]}
                ),
                direction="both",
                active=True,
                **values,
            )
        )
    for name, title in (
        ("s", "Demo Welcome Centre"),
        ("t", "Demo Library"),
        ("b", "Demo Learning Hall"),
    ):
        db.add(
            Location(
                id=demo_id("location:" + name),
                campus_id=campus_id,
                name=title,
                kind="building",
                description="Synthetic demonstration building",
                point=geometry({"type": "Point", "coordinates": POSITIONS[name]}),
                active=True,
            )
        )
    db.flush()
    for name in ("s", "t", "b"):
        db.add(
            AccessPoint(
                campus_id=campus_id,
                location_id=demo_id("location:" + name),
                node_id=demo_id("node:" + name),
                label="Demonstration entrance",
                kind="entrance",
                is_primary=True,
            )
        )
    for name, node, kind, edge in (
        ("ramp", "b", "ramp", "ramp-cross"),
        ("entrance", "t", "entrance", "upper-east"),
    ):
        db.add(
            Infrastructure(
                id=demo_id("infrastructure:" + name),
                campus_id=campus_id,
                location_id=demo_id("location:" + node),
                name="Demo " + name,
                kind=kind,
                point=geometry({"type": "Point", "coordinates": POSITIONS[node]}),
                accessibility="accessible",
                availability="open",
                active=True,
                **verified,
            )
        )
        db.flush()
        db.add(
            InfrastructureEdge(
                campus_id=campus_id,
                infrastructure_id=demo_id("infrastructure:" + name),
                edge_id=demo_id("edge:" + edge),
            )
        )
    db.add(GraphState(campus_id=campus_id, version=1, next_expiry_at=now + timedelta(days=30)))
    db.add(
        GraphEvent(
            campus_id=campus_id,
            graph_version=1,
            event_type="graph.reset",
            changed_edge_ids=[demo_id("edge:" + e[0]) for e in EDGES],
            reason="synthetic_seed",
        )
    )
    db.flush()
    return (
        "Synthetic campus seeded: 9 nodes, 13 physical edges, 3 locations, 2 infrastructure records"
    )
