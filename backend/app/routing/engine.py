"""Pure directed-multigraph routing with proven ECEF A* and bounded Yen search.

Only standard-library types cross this boundary. Distances are supplied by the
PostGIS adapter; a WGS84 chord invariant is checked here before A* can execute.
"""

import heapq
import itertools
import math
import time
from collections import Counter, defaultdict, deque
from collections.abc import Callable
from datetime import datetime

from .domain import (
    Arc,
    ArcReference,
    Calculation,
    Dependency,
    Edge,
    EndpointNotFound,
    GraphInvalid,
    GraphSnapshot,
    Instruction,
    Node,
    Point,
    Profile,
    Route,
    RoutingBudgetExceeded,
    SearchLimits,
    SearchStats,
    Verification,
    Warning,
)

SURFACE_FACTOR = {"smooth": 0.0, "uneven": 0.30, "gravel": 0.50, "unknown": 0.15}
WARNING_MESSAGES = {
    "UNKNOWN_ACCESSIBILITY": "Accessibility is unknown on one or more traversed paths.",
    "UNVERIFIED_OBSERVATION": "Some path observations are unverified, expired, or need review.",
    "MISSING_OBSERVATION": "Some path measurements are missing; their accessibility is uncertain.",
    "DEPENDENCY_UNCERTAINTY": "Mapped infrastructure has unknown or noncurrent observations.",
    "DURATION_ESTIMATE": "Duration is a walking-speed estimate and excludes unmeasured delays.",
    "SYNTHETIC_DATA": "This route uses fictional demonstration data, not a surveyed campus.",
}


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _aware(value: datetime) -> bool:
    return (
        isinstance(value, datetime) and value.tzinfo is not None and value.utcoffset() is not None
    )


def _point(point: Point) -> None:
    if (
        len(point) != 2
        or not all(_finite(value) for value in point)
        or not -180 <= point[0] <= 180
        or not -90 <= point[1] <= 90
    ):
        raise GraphInvalid("Coordinates must be finite WGS84 longitude/latitude pairs")


def ecef(point: Point) -> tuple[float, float, float]:
    """WGS84 ellipsoidal-height-zero coordinates, in metres."""
    _point(point)
    lon, lat = map(math.radians, point)
    flattening = 1 / 298.257223563
    eccentricity_squared = flattening * (2 - flattening)
    radius = 6_378_137 / math.sqrt(1 - eccentricity_squared * math.sin(lat) ** 2)
    return (
        radius * math.cos(lat) * math.cos(lon),
        radius * math.cos(lat) * math.sin(lon),
        radius * (1 - eccentricity_squared) * math.sin(lat),
    )


def chord_distance(a: Point, b: Point) -> float:
    return math.dist(ecef(a), ecef(b))


def edge_cost(edge: Edge, uncertain: bool) -> float:
    """walking-effort-v1; uncertainty never fabricates a missing measurement."""
    grade = abs(edge.slope_pct) / 100 if edge.slope_pct is not None else 0.0
    cost = edge.distance_m * (1 + 2 * grade + SURFACE_FACTOR[edge.surface] + 0.5 * uncertain)
    if not math.isfinite(cost) or cost < edge.distance_m:
        raise GraphInvalid("Edge cost must be finite and at least physical distance")
    return cost


class _Budget:
    def __init__(self, limits: SearchLimits, clock: Callable[[], float] = time.perf_counter):
        if (
            type(limits.max_expansions) is not int
            or limits.max_expansions < 0
            or not _finite(limits.max_seconds)
            or limits.max_seconds < 0
            or type(limits.max_alternative_candidates) is not int
            or not 0 <= limits.max_alternative_candidates <= 20
        ):
            raise ValueError("Routing budgets must be nonnegative; candidate cap cannot exceed 20")
        self.limits = limits
        self.clock = clock
        self.started = clock()
        self.expansions = 0
        self.searches = 0
        self.alternative_candidates = 0

    def check(self) -> None:
        if self.clock() - self.started >= self.limits.max_seconds:
            raise RoutingBudgetExceeded("Routing execution time budget exceeded")

    def expand(self) -> None:
        self.check()
        if self.expansions >= self.limits.max_expansions:
            raise RoutingBudgetExceeded("Routing expansion budget exceeded")
        self.expansions += 1

    def stats(self) -> SearchStats:
        return SearchStats(
            expansions=self.expansions,
            searches=self.searches,
            elapsed_ms=(self.clock() - self.started) * 1000,
            alternative_candidates=self.alternative_candidates,
        )


def _profile(profile: Profile) -> None:
    if (
        type(profile.avoid_stairs) is not bool
        or profile.unknown_policy not in {"exclude", "allow_with_warning"}
        or not set(profile.excluded_surfaces) <= {"smooth", "uneven", "gravel"}
        or not _finite(profile.travel_speed_mps)
        or not 0.1 <= profile.travel_speed_mps <= 3
    ):
        raise ValueError("Invalid routing profile")
    if profile.max_slope_pct is not None and (
        not _finite(profile.max_slope_pct) or not 0 <= profile.max_slope_pct <= 100
    ):
        raise ValueError("Invalid slope constraint")
    if profile.min_width_m is not None and (
        not _finite(profile.min_width_m) or not 0 < profile.min_width_m <= 10
    ):
        raise ValueError("Invalid width constraint")


def _observation(record: Edge | Dependency) -> None:
    if (
        not isinstance(record.id, str)
        or not record.id
        or record.accessibility not in {"accessible", "inaccessible", "unknown"}
        or record.availability not in {"open", "closed", "temporarily_blocked"}
        or record.verification not in {"verified", "unverified", "needs_review"}
        or type(record.active) is not bool
        or (record.expires_at is not None and not _aware(record.expires_at))
    ):
        raise GraphInvalid("Invalid graph observation")


def _validate(snapshot: GraphSnapshot, budget: _Budget) -> dict[str, Node]:
    if not _aware(snapshot.evaluated_at) or snapshot.data_origin not in {
        "synthetic_demo",
        "surveyed",
    }:
        raise GraphInvalid("Snapshot requires an aware evaluation time and known data origin")
    nodes: dict[str, Node] = {}
    for node in snapshot.nodes:
        budget.check()
        if not isinstance(node.id, str) or not node.id or node.id in nodes:
            raise GraphInvalid("Node identities must be unique nonempty strings")
        if type(node.active) is not bool or (
            node.name is not None and not isinstance(node.name, str)
        ):
            raise GraphInvalid("Invalid node metadata")
        _point(node.point)
        nodes[node.id] = node
    edge_ids: set[str] = set()
    dependencies: dict[str, Dependency] = {}
    for edge in snapshot.edges:
        budget.check()
        _observation(edge)
        if (
            edge.id in edge_ids
            or edge.source_id not in nodes
            or edge.target_id not in nodes
            or edge.source_id == edge.target_id
        ):
            raise GraphInvalid("Edge identities and endpoint associations must be valid")
        edge_ids.add(edge.id)
        if (
            edge.direction not in {"both", "forward", "reverse"}
            or edge.surface not in SURFACE_FACTOR
            or type(edge.restricted) is not bool
            or not _finite(edge.distance_m)
            or edge.distance_m <= 0
            or len(edge.geometry) < 2
            or len(edge.geometry) > 1000
        ):
            raise GraphInvalid("Invalid distance, geometry, direction, or surface")
        if edge.width_m is not None and (not _finite(edge.width_m) or not 0 < edge.width_m <= 10):
            raise GraphInvalid("Invalid width observation")
        if edge.slope_pct is not None and (
            not _finite(edge.slope_pct) or not -100 <= edge.slope_pct <= 100
        ):
            raise GraphInvalid("Invalid slope observation")
        if any(
            value is not None and type(value) is not bool
            for value in (edge.has_stairs, edge.has_ramp)
        ):
            raise GraphInvalid("Stairs and ramp observations must be booleans or absent")
        for point in edge.geometry:
            _point(point)
        source, target = nodes[edge.source_id], nodes[edge.target_id]
        if edge.geometry[0] != source.point or edge.geometry[-1] != target.point:
            raise GraphInvalid("Edge geometry endpoints must exactly match path nodes")
        if edge.distance_m < chord_distance(source.point, target.point):
            raise GraphInvalid("Edge distance violates the ECEF lower bound")
        seen_dependencies: set[str] = set()
        for dependency in edge.dependencies:
            _observation(dependency)
            if dependency.id in seen_dependencies:
                raise GraphInvalid("An edge cannot repeat a mapped dependency")
            seen_dependencies.add(dependency.id)
            previous = dependencies.get(dependency.id)
            if previous is not None and previous != dependency:
                raise GraphInvalid("Mapped dependency has inconsistent snapshot observations")
            dependencies[dependency.id] = dependency
        # Check overflow even for records later excluded by the request profile.
        edge_cost(edge, True)
    return nodes


def _current(record: Edge | Dependency, evaluated_at: datetime) -> bool:
    return (
        record.verification == "verified"
        and record.expires_at is not None
        and record.expires_at > evaluated_at
    )


def _eligibility(
    edge: Edge, nodes: dict[str, Node], profile: Profile, at: datetime
) -> tuple[frozenset[str], frozenset[str]]:
    reasons: set[str] = set()
    warnings: set[str] = set()
    current = _current(edge, at)
    if not edge.active:
        reasons.add("inactive_edge")
    if not nodes[edge.source_id].active or not nodes[edge.target_id].active:
        reasons.add("inactive_node")
    if edge.availability != "open":
        reasons.add("closed")
    if edge.restricted:
        reasons.add("restricted")
    if edge.accessibility == "inaccessible":
        reasons.add("inaccessible")
    if edge.accessibility == "unknown":
        warnings.add("UNKNOWN_ACCESSIBILITY")
    if not current:
        warnings.add("UNVERIFIED_OBSERVATION")
    if (
        any(value is None for value in (edge.has_stairs, edge.width_m, edge.slope_pct))
        or edge.surface == "unknown"
    ):
        warnings.add("MISSING_OBSERVATION")
    for dependency in edge.dependencies:
        if not dependency.active or dependency.availability != "open":
            reasons.add("unavailable_dependency")
        if dependency.accessibility == "inaccessible":
            reasons.add("inaccessible_dependency")
        if not _current(dependency, at) or dependency.accessibility == "unknown":
            warnings.add("DEPENDENCY_UNCERTAINTY")
    if profile.avoid_stairs:
        if edge.has_stairs is True:
            reasons.add("stairs")
        if not current or edge.has_stairs is None:
            reasons.add("unproven_stairs")
    if profile.max_slope_pct is not None:
        if edge.slope_pct is not None and abs(edge.slope_pct) > profile.max_slope_pct:
            reasons.add("slope_limit")
        if not current or edge.slope_pct is None:
            reasons.add("unproven_slope")
    if profile.min_width_m is not None:
        if edge.width_m is not None and edge.width_m < profile.min_width_m:
            reasons.add("width_limit")
        if not current or edge.width_m is None:
            reasons.add("unproven_width")
    if profile.excluded_surfaces:
        if edge.surface in profile.excluded_surfaces:
            reasons.add("excluded_surface")
        if not current or edge.surface == "unknown":
            reasons.add("unproven_surface")
    if profile.unknown_policy == "exclude":
        mapping = {
            "UNKNOWN_ACCESSIBILITY": "unknown_accessibility",
            "UNVERIFIED_OBSERVATION": "unverified_observation",
            "MISSING_OBSERVATION": "missing_observation",
            "DEPENDENCY_UNCERTAINTY": "dependency_uncertainty",
        }
        reasons.update(mapping[code] for code in warnings)
    return frozenset(reasons), frozenset(warnings)


def _arcs(edge: Edge, warning_codes: frozenset[str]) -> tuple[Arc, ...]:
    arcs = []
    cost = edge_cost(edge, bool(warning_codes))
    if edge.direction in {"both", "forward"}:
        arcs.append(
            Arc(
                edge,
                "forward",
                edge.source_id,
                edge.target_id,
                edge.geometry,
                edge.slope_pct,
                cost,
                bool(warning_codes),
                warning_codes,
            )
        )
    if edge.direction in {"both", "reverse"}:
        slope = -edge.slope_pct if edge.slope_pct is not None else None
        arcs.append(
            Arc(
                edge,
                "reverse",
                edge.target_id,
                edge.source_id,
                tuple(reversed(edge.geometry)),
                slope,
                cost,
                bool(warning_codes),
                warning_codes,
            )
        )
    return tuple(arcs)


def _search(
    adjacency: dict[str, tuple[Arc, ...]],
    nodes: dict[str, Node],
    source: str,
    target: str,
    algorithm: str,
    budget: _Budget,
    blocked_nodes: frozenset[str] = frozenset(),
    blocked_arcs: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[Arc, ...] | None:
    budget.searches += 1
    budget.check()
    if source in blocked_nodes or target in blocked_nodes:
        return None
    destination = ecef(nodes[target].point)
    heuristic_cache: dict[str, float] = {}

    def heuristic(node_id: str) -> float:
        if algorithm == "dijkstra":
            return 0.0
        if node_id not in heuristic_cache:
            heuristic_cache[node_id] = math.dist(ecef(nodes[node_id].point), destination)
        return heuristic_cache[node_id]

    sequence = itertools.count()
    heap = [(heuristic(source), 0.0, source, next(sequence))]
    scores = {source: 0.0}
    predecessors: dict[str, Arc] = {}
    while heap:
        budget.check()
        _, distance, node_id, _ = heapq.heappop(heap)
        if distance != scores[node_id]:
            continue
        budget.expand()
        if node_id == target:
            path = []
            while node_id != source:
                arc = predecessors[node_id]
                path.append(arc)
                node_id = arc.source_id
            return tuple(reversed(path))
        for arc in adjacency.get(node_id, ()):
            if arc.target_id in blocked_nodes or arc.identity in blocked_arcs:
                continue
            candidate = distance + arc.cost
            if not math.isfinite(candidate):
                raise GraphInvalid("Accumulated route cost overflow")
            if candidate < scores.get(arc.target_id, math.inf):
                scores[arc.target_id] = candidate
                predecessors[arc.target_id] = arc
                priority = candidate + heuristic(arc.target_id)
                if not math.isfinite(priority):
                    raise GraphInvalid("Route priority overflow")
                heapq.heappush(heap, (priority, candidate, arc.target_id, next(sequence)))
    return None


def _structurally_connected(
    snapshot: GraphSnapshot, nodes: dict[str, Node], source: str, target: str, budget: _Budget
) -> bool:
    if not nodes[source].active or not nodes[target].active:
        return False
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in snapshot.edges:
        budget.check()
        if not edge.active or not nodes[edge.source_id].active or not nodes[edge.target_id].active:
            continue
        if edge.direction in {"both", "forward"}:
            adjacency[edge.source_id].append(edge.target_id)
        if edge.direction in {"both", "reverse"}:
            adjacency[edge.target_id].append(edge.source_id)
    pending = deque([source])
    seen = {source}
    while pending:
        budget.expand()
        node_id = pending.popleft()
        if node_id == target:
            return True
        for neighbor in adjacency.get(node_id, ()):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return False


def _path_cost(path: tuple[Arc, ...]) -> float:
    # Identical left-to-right summation to the shortest-path relaxation sequence.
    return sum(arc.cost for arc in path)


def _path_identity(path: tuple[Arc, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(arc.identity for arc in path)


def _diverse(path: tuple[Arc, ...], accepted: tuple[Arc, ...]) -> bool:
    physical = {arc.edge.id for arc in accepted}
    # Loopless node paths cannot traverse the same physical edge more than once.
    shared = sum(arc.edge.distance_m for arc in path if arc.edge.id in physical)
    shorter = min(
        sum(arc.edge.distance_m for arc in path), sum(arc.edge.distance_m for arc in accepted)
    )
    return shared <= 0.8 * shorter


def _alternatives(
    primary: tuple[Arc, ...],
    adjacency: dict[str, tuple[Arc, ...]],
    nodes: dict[str, Node],
    source: str,
    target: str,
    count: int,
    budget: _Budget,
) -> tuple[tuple[tuple[Arc, ...], ...], bool]:
    """Yen enumerates at most 20 additional popped loopless path candidates.

    Rejected diversity candidates still participate in Yen partitioning; otherwise
    a valid later alternative could disappear. All spur searches share the global
    request time/expansion budget. Exhausting that budget preserves the optimum.
    """
    if count == 0 or not primary:
        return (), True
    enumerated = [primary]
    accepted: list[tuple[Arc, ...]] = []
    candidates: list[tuple[float, tuple[tuple[str, str], ...], tuple[Arc, ...]]] = []
    candidate_ids = {_path_identity(primary)}
    optimum = _path_cost(primary)
    try:
        while len(accepted) < count:
            if budget.alternative_candidates >= budget.limits.max_alternative_candidates:
                return tuple(accepted), False
            previous = enumerated[-1]
            previous_nodes = (source,) + tuple(arc.target_id for arc in previous)
            for index, spur_node in enumerate(previous_nodes[:-1]):
                budget.check()
                root = previous[:index]
                root_ids = _path_identity(root)
                blocked_arcs = frozenset(
                    path[index].identity
                    for path in enumerated
                    if len(path) > index and _path_identity(path[:index]) == root_ids
                )
                spur = _search(
                    adjacency,
                    nodes,
                    spur_node,
                    target,
                    "dijkstra",
                    budget,
                    frozenset(previous_nodes[:index]),
                    blocked_arcs,
                )
                if spur is None:
                    continue
                candidate = root + spur
                identity = _path_identity(candidate)
                cost = _path_cost(candidate)
                if identity not in candidate_ids:
                    candidate_ids.add(identity)
                    if cost <= 1.5 * optimum:
                        heapq.heappush(candidates, (cost, identity, candidate))
            if not candidates:
                return tuple(accepted), True
            _, _, candidate = heapq.heappop(candidates)
            budget.alternative_candidates += 1
            enumerated.append(candidate)
            if all(_diverse(candidate, route) for route in (primary, *accepted)):
                accepted.append(candidate)
        return tuple(accepted), True
    except RoutingBudgetExceeded:
        return tuple(accepted), False


def _bearing(a: Point, b: Point) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    return math.degrees(
        math.atan2(
            math.sin(lon2 - lon1) * math.cos(lat2),
            math.cos(lat1) * math.sin(lat2)
            - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1),
        )
    )


def _heading(geometry: tuple[Point, ...], *, beginning: bool) -> float | None:
    pairs = tuple(zip(geometry, geometry[1:], strict=False))
    for a, b in pairs if beginning else reversed(pairs):
        if a != b:
            return _bearing(a, b)
    return None


def _instructions(path: tuple[Arc, ...], nodes: dict[str, Node]) -> tuple[Instruction, ...]:
    result = []
    previous_heading = None
    for index, arc in enumerate(path):
        heading = _heading(arc.geometry, beginning=True)
        maneuver = "depart" if index == 0 else "continue"
        if previous_heading is not None and heading is not None:
            angle = (heading - previous_heading + 180) % 360 - 180
            if abs(angle) >= 150:
                maneuver = "turn_back"
            elif angle >= 30:
                maneuver = "turn_right"
            elif angle <= -30:
                maneuver = "turn_left"
        destination = nodes[arc.target_id].name or "the next mapped junction"
        action = {
            "depart": "Start",
            "continue": "Continue",
            "turn_right": "Turn right",
            "turn_left": "Turn left",
            "turn_back": "Turn back",
        }[maneuver]
        text = f"{action} toward {destination} for {arc.edge.distance_m:.0f} m."
        if arc.edge.has_stairs is True:
            text += " Recorded stairs are present."
        if arc.uncertain:
            text += " Some accessibility observations are uncertain."
        result.append(
            Instruction(
                arc.edge.id, arc.edge.distance_m, text, maneuver, arc.target_id, arc.slope_pct
            )
        )
        previous_heading = _heading(arc.geometry, beginning=False)
    return tuple(result)


def _warnings(codes: dict[str, set[str]]) -> tuple[Warning, ...]:
    return tuple(
        Warning(code, WARNING_MESSAGES[code], tuple(sorted(edge_ids)))
        for code, edge_ids in sorted(codes.items())
    )


def _route(
    path: tuple[Arc, ...],
    source: str,
    nodes: dict[str, Node],
    profile: Profile,
    snapshot: GraphSnapshot,
) -> Route:
    coordinates: list[Point] = []
    codes: dict[str, set[str]] = {"DURATION_ESTIMATE": set()}
    if snapshot.data_origin == "synthetic_demo":
        codes["SYNTHETIC_DATA"] = set()
    verified = []
    uncertain = []
    expiries = []
    for arc in path:
        coordinates.extend(arc.geometry if not coordinates else arc.geometry[1:])
        (uncertain if arc.uncertain else verified).append(arc.edge.distance_m)
        for code in arc.warning_codes:
            codes.setdefault(code, set()).add(arc.edge.id)
        for record in (arc.edge, *arc.edge.dependencies):
            if _current(record, snapshot.evaluated_at):
                expiries.append(record.expires_at)
    geometry = (
        {"type": "LineString", "coordinates": coordinates}
        if path
        else {"type": "Point", "coordinates": nodes[source].point}
    )
    distance = sum(arc.edge.distance_m for arc in path)
    duration = distance / profile.travel_speed_mps
    if not math.isfinite(distance) or not math.isfinite(duration):
        raise GraphInvalid("Route physical totals overflow")
    return Route(
        node_ids=(source,) + tuple(arc.target_id for arc in path),
        arcs=tuple(ArcReference(arc.edge.id, arc.direction) for arc in path),
        geometry=geometry,
        total_distance_m=distance,
        estimated_duration_s=duration,
        cost_m_equivalent=_path_cost(path),
        instructions=_instructions(path, nodes),
        verification=Verification(
            summary="contains_uncertainty" if uncertain else "observations_current",
            verified_distance_m=sum(verified),
            uncertain_distance_m=sum(uncertain),
            earliest_expiry_at=min(expiries) if expiries else None,
        ),
        warnings=_warnings(codes),
    )


def calculate(
    snapshot: GraphSnapshot,
    source_id: str,
    destination_id: str,
    profile: Profile,
    algorithm: str = "astar",
    alternatives_limit: int = 0,
    limits: SearchLimits = SearchLimits(),
) -> Calculation:
    """Validate, filter once, and calculate against exactly one immutable snapshot."""
    if algorithm not in {"dijkstra", "astar"}:
        raise ValueError("Unsupported routing algorithm")
    if type(alternatives_limit) is not int or not 0 <= alternatives_limit <= 2:
        raise ValueError("At most two additional routes may be requested")
    _profile(profile)
    budget = _Budget(limits)
    nodes = _validate(snapshot, budget)
    if source_id not in nodes or destination_id not in nodes:
        raise EndpointNotFound("Requested path node is absent from the snapshot")
    adjacency: dict[str, list[Arc]] = defaultdict(list)
    excluded: Counter[str] = Counter()
    for edge in snapshot.edges:
        budget.check()
        reasons, warning_codes = _eligibility(edge, nodes, profile, snapshot.evaluated_at)
        excluded.update(reasons)
        if not reasons:
            for arc in _arcs(edge, warning_codes):
                adjacency[arc.source_id].append(arc)
    stable_adjacency = {
        node: tuple(sorted(arcs, key=lambda arc: (arc.target_id, arc.identity)))
        for node, arcs in adjacency.items()
    }
    path = None
    if nodes[source_id].active and nodes[destination_id].active:
        path = _search(stable_adjacency, nodes, source_id, destination_id, algorithm, budget)
    excluded_counts = dict(sorted(excluded.items()))
    if path is None:
        connected = _structurally_connected(snapshot, nodes, source_id, destination_id, budget)
        codes = {"SYNTHETIC_DATA": set()} if snapshot.data_origin == "synthetic_demo" else {}
        return Calculation(
            "no_route",
            "constraints_exclude_all_paths" if connected else "disconnected",
            excluded_counts,
            None,
            (),
            True,
            _warnings(codes),
            budget.stats(),
        )
    alternatives, exhaustive = _alternatives(
        path, stable_adjacency, nodes, source_id, destination_id, alternatives_limit, budget
    )
    primary = _route(path, source_id, nodes, profile, snapshot)
    alternative_routes = tuple(
        _route(other, source_id, nodes, profile, snapshot) for other in alternatives
    )
    warnings: dict[str, set[str]] = {}
    for warning in primary.warnings:
        if warning.code in {"DURATION_ESTIMATE", "SYNTHETIC_DATA"}:
            warnings.setdefault(warning.code, set()).update(warning.edge_ids)
    return Calculation(
        "found",
        None,
        excluded_counts,
        primary,
        alternative_routes,
        exhaustive,
        _warnings(warnings),
        budget.stats(),
    )
