"""Immutable, dependency-free routing inputs and serializable domain outputs."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

Point = tuple[float, float]
POLICY_VERSION = "accessibility-v1"
COST_MODEL_VERSION = "walking-effort-v1"


class GraphInvalid(ValueError):
    """The stored graph cannot support the declared routing guarantees."""


class EndpointNotFound(ValueError):
    """A requested path-node identity is absent from this snapshot."""


class RoutingBudgetExceeded(RuntimeError):
    """No primary answer has been established within the execution budget."""


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    point: Point
    name: str | None = None
    active: bool = True

    def __post_init__(self):
        object.__setattr__(self, "point", tuple(self.point))


@dataclass(frozen=True, slots=True)
class Dependency:
    id: str
    accessibility: str = "unknown"
    availability: str = "open"
    verification: str = "unverified"
    expires_at: datetime | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class Edge:
    id: str
    source_id: str
    target_id: str
    geometry: tuple[Point, ...]
    distance_m: float
    direction: str = "both"
    accessibility: str = "unknown"
    availability: str = "open"
    verification: str = "unverified"
    expires_at: datetime | None = None
    width_m: float | None = None
    slope_pct: float | None = None
    surface: str = "unknown"
    has_stairs: bool | None = None
    has_ramp: bool | None = None
    active: bool = True
    dependencies: tuple[Dependency, ...] = ()
    restricted: bool = False

    def __post_init__(self):
        object.__setattr__(self, "geometry", tuple(tuple(point) for point in self.geometry))
        object.__setattr__(self, "dependencies", tuple(self.dependencies))


@dataclass(frozen=True, slots=True)
class Profile:
    avoid_stairs: bool = False
    max_slope_pct: float | None = None
    min_width_m: float | None = None
    excluded_surfaces: tuple[str, ...] = ()
    unknown_policy: str = "exclude"
    travel_speed_mps: float = 1.0

    def __post_init__(self):
        object.__setattr__(self, "excluded_surfaces", tuple(sorted(set(self.excluded_surfaces))))


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    evaluated_at: datetime
    data_origin: str = "synthetic_demo"

    def __post_init__(self):
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))


@dataclass(frozen=True, slots=True)
class SearchLimits:
    max_expansions: int = 100_000
    max_seconds: float = 2.0
    max_alternative_candidates: int = 20


@dataclass(frozen=True, slots=True)
class Warning:
    code: str
    message: str
    edge_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ArcReference:
    edge_id: str
    direction: str


@dataclass(frozen=True, slots=True)
class Instruction:
    edge_id: str
    distance_m: float
    text: str
    maneuver: str
    node_id: str
    slope_pct: float | None


@dataclass(frozen=True, slots=True)
class Verification:
    summary: str
    verified_distance_m: float
    uncertain_distance_m: float
    earliest_expiry_at: datetime | None


@dataclass(frozen=True, slots=True)
class Route:
    node_ids: tuple[str, ...]
    arcs: tuple[ArcReference, ...]
    geometry: dict[str, Any]
    total_distance_m: float
    estimated_duration_s: float
    cost_m_equivalent: float
    instructions: tuple[Instruction, ...]
    verification: Verification
    warnings: tuple[Warning, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SearchStats:
    expansions: int
    searches: int
    elapsed_ms: float
    alternative_candidates: int


@dataclass(frozen=True, slots=True)
class Calculation:
    status: str
    reason: str | None
    excluded_edge_counts: dict[str, int]
    primary: Route | None
    alternatives: tuple[Route, ...]
    alternatives_exhaustive: bool
    warnings: tuple[Warning, ...]
    stats: SearchStats

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Arc:
    """Internal directed expansion; physical IDs survive parallel arcs."""

    edge: Edge
    direction: str
    source_id: str
    target_id: str
    geometry: tuple[Point, ...]
    slope_pct: float | None
    cost: float
    uncertain: bool
    warning_codes: frozenset[str] = field(default_factory=frozenset)

    @property
    def identity(self) -> tuple[str, str]:
        return self.edge.id, self.direction
