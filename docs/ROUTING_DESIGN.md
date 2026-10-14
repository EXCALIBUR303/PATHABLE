# Routing design and correctness contract

Implemented through Phase 4 in `backend/app/routing`, the PostGIS adapter and the route UI. [ADR-012](adr/012-phase3-routing.md) records implementation bounds and snapshot/currentness decisions; [Phase 3 evidence](PHASE3_TEST_EVIDENCE.md) records executed checks. The Phase 0 JSON fixture and validator remain a separate design oracle. Phase 4 implements the source-specific restriction ledger in coherent snapshots and SSE-driven route retirement/recalculation; see [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md).

## Graph and endpoints

For one campus, `G=(V,A)` is a directed multigraph expanded from physical `path_edges`. Node IDs are stable UUIDs; each arc has `(physical_edge_id, direction)` identity, ordered geometry, and nonnegative cost. `both` emits two arcs, `forward` source→target, `reverse` target→source. Reverse geometry and signed slope with the arc; apply slope limits to absolute grade initially. No implicit connection at a visual crossing, centroid, or matching XY on another level. An unavailable node excludes incident arcs. Active mapped infrastructure restrictions apply to all dependent physical edges.

Route requests use **path-node IDs**, chosen from location access points. No arbitrary GPS snapping in this version. A known same-node request yields a valid zero-distance route with a GeoJSON Point and no edges/instructions; graph edges themselves must have positive distance. Unknown IDs produce 404, cross-campus IDs 422. Disconnected valid nodes yield a structured `no_route` result (HTTP 200).

## Accessibility and hard eligibility

Evaluate effective availability first: any baseline closure, active verified-report/manual restriction, or unavailable mapped infrastructure excludes the edge. Administrative closures apply regardless of whether a descriptive accessibility survey is current. Unreviewed reports and predictions never create these restrictions.

Then reject known `inaccessible` edges. Apply the profile:

| Constraint | Eligibility rule |
| --- | --- |
| avoid_stairs=true | has_stairs must be false and its record currently verified |
| max_slope_pct set | known currently verified absolute slope <= limit |
| min_width_m set | known currently verified width >= limit |
| excluded_surfaces nonempty | known currently verified surface not in excluded set |
| unknown_policy=exclude | reject any unknown accessibility, missing relevant observation, unverified/stale edge or dependent infrastructure |
| unknown_policy=allow_with_warning | permit uncertain records only where they do not prevent proving a hard constraint; annotate uncertainty and apply cost penalty |

For policy `exclude`, core relevant observations are accessibility, stairs, width, slope, and surface plus verification of the edge and mapped infrastructure. `has_ramp` is descriptive; missing it alone does not prove or disprove access. `accessible` never overrides stairs or numeric limits. For a wheelchair preset choose avoid stairs=true, max slope=8%, min width=0.9m, excluded surfaces=[uneven,gravel], unknown=exclude. This is a configurable product default, **not a legal accessibility standard or guarantee**. General default also excludes unknown data; users may explicitly choose a permissive uncertainty policy. Saved values and per-request overrides resolve once into a complete echoed profile; missing requests do not silently use a permissive preset.

Numeric values must be finite and in API bounds. Hard comparisons use actual values, not a cost tolerance that relaxes a physical limit. Unverified measurements cannot prove compliance. A known stairs=false field in an unverified record is not certified safe for an avoid-stairs request.

## Cost, distance, and duration

Version `walking-effort-v1` uses metre-equivalent weighted cost:

```text
grade = abs(slope_pct) / 100                 # if known, else 0 for this term only
surface_factor = smooth:0, uneven:0.30, gravel:0.50, unknown:0.15
uncertainty = 1 if any eligible uncertain edge/dependency data else 0
c(arc) = distance_m * (1 + 2*grade + surface_factor + 0.50*uncertainty)
route_cost_m_equivalent = sum(c(arc))
total_distance_m = sum(distance_m)
estimated_duration_s = total_distance_m / travel_speed_mps
```

Missing slope contributes no *numeric slope term* only after eligibility has allowed it; uncertainty still applies and the raw value remains NULL. All terms are nonnegative, so `c >= distance_m > 0`. Physical distance is `ST_Length(LineString::geography)` using the WGS84 spheroid; never subtract lat/lon and call the result metres. Duration is a walking-speed estimate, not a measured traversal time; delays/elevator times are out of scope until measured. Weighted cost is never displayed as physical distance or duration. No user-specified negative weights; server constants and profile/cost-model fingerprints are versioned.

## A* heuristic and proof obligations

Use `h(v) = ||ECEF(v)-ECEF(goal)||`, in metres on WGS84 at ellipsoidal height zero. For latitude φ, longitude λ, `a=6378137`, `f=1/298.257223563`, `e²=f(2-f)`, `N=a/sqrt(1-e² sin²φ)`:

```text
x = N cosφ cosλ
y = N cosφ sinλ
z = N(1-e²) sinφ
```

The straight chord is no longer than the surface path between exact endpoints. Graph ingestion requires `distance_m >= chord(u,v)` for every edge. Euclidean triangle inequality gives `h(u) <= chord(u,v)+h(v) <= c(u,v)+h(v)`; therefore the heuristic is consistent and admissible, and h(goal)=0. Hard filtering removes edges but preserves this inequality. Do not substitute a spherical haversine distance for the chord while retaining spheroidal edge lengths without a separate proof. If future cost discounts, teleport edges, or invalid geometry break the lower bound, reject the graph or deliberately use h=0 with a recorded diagnostic; do not claim heuristic optimality silently.

Use float64, reject NaN/Infinity, and sum route totals consistently. Algorithm comparison tolerance: absolute `1e-6` metre-equivalent or relative `1e-9`, whichever is larger. This tolerance is for result comparison, never for admitting prohibited edges. Do not round edge costs before searching. Heap ordering uses `(priority, accumulated_cost, stable_node_id, insertion_sequence)`; ignore stale heap entries. Relax on strictly lower numeric cost; do not suppress a genuinely shorter route with an arbitrary epsilon. Reconstruct using predecessor arc IDs, not only predecessor nodes, because parallel arcs may exist.

Dijkstra with binary heap: `O((|V|+|A|) log |V|)` for the usual indexed-heap bound (lazy duplicate heap implementation is `O((|V|+|A|) log |A|)`); memory O(V+A). A* has the same worst-case bound and may explore fewer nodes. Early terminate only when the goal is popped with current best score under the proven heuristic. Equal-cost paths may differ; compare costs and validity rather than exact node order between algorithms. Apply request time/expansion budgets, returning explicit 503 `ROUTING_BUDGET_EXCEEDED` instead of a false no-route answer.

## Alternatives

Use bounded Yen loopless K-shortest paths on the **same filtered directed multigraph and cost model**, using Dijkstra as the spur-path primitive. Seek at most 3 routes including the optimum; deduplicate by ordered arc identities. Reject alternatives with >80% shared physical distance of the shorter route, or cost >1.5× optimum; enumerate at most 20 candidates. Shared distance uses shared physical edge lengths, so reversing the same corridor does not masquerade as diversity. Return fewer alternatives when criteria cannot be met and set `alternatives_exhaustive=false` if candidate/time budget stopped enumeration. Primary optimality is separate from alternative completeness. Source=destination returns no alternatives. Approximate upper bound with candidate cap B is O(B·|V|·(|A|+|V|) log|V|); keep this bounded for interactive use.

## Snapshot, aging, and currentness

1. Before snapshot load, check graph_state.next_expiry_at using database UTC. If due, acquire graph lock, mark due verified records `needs_review`, increment affected row versions, increment graph version once, insert event, compute next expiry, commit. A background maintenance task also performs this to notify idle clients. It is idempotent under concurrent requests.
2. Load graph_state and graph records/restrictions within one repeatable-read transaction. Set `valid_until` to earliest remaining verified observation expiry. Fail 503 if graph integrity is invalid; never substitute a fabricated graph.
3. Filter and search without mutating the snapshot. Attach graph_version, policy/cost-model versions, profile fingerprint, `validated_at`, and `valid_until`.
4. Compare latest version and freshness deadline just before response. On mismatch, rebuild/recompute once. Further changes return 409 `GRAPH_CHANGED_RETRY` with latest version. A route is current only at that validation instant; events and client expiry handle later changes.
5. No initial result cache. If introduced, key by campus, graph_version, policy_version, cost_model_version, source, destination, full canonical profile and algorithm/alternative options. Never serve beyond valid_until, use an obsolete revision as current, or reuse stale memory after DB reconnect without version validation.

## Results and explanations

`found` includes node and directional-edge sequences, Point/LineString GeoJSON, real distance, estimated duration, cost, instruction segments, warnings, and verification summaries. Every alternative has its own totals/geometry but shares snapshot/profile identity. A joined LineString removes duplicate junction coordinates; Point is allowed only for a zero-edge route.

`no_route` has no fake geometry or distance. Include profile, graph version, origin/destination, `reason` (`disconnected` or `constraints_exclude_all_paths`) and counts by exclusion reason. To distinguish these reasons, run a bounded reachability check on structurally valid active-node connectivity without profile/availability filtering. Counts describe excluded graph edges, not a claim that relaxing any one constraint guarantees a route; do not automatically relax a user's restrictions. Budget exhaustion remains a separate service error.

Turn instructions derive from ordered route geometry and known landmark/access-point metadata. Unknown data produces explicit wording, not invented ramps or accessible entrances. A UI can compare distance/cost/warnings but must not label any result “verified safe.”

## Required proof and test evidence

Phase 3 must compare both algorithms to exhaustive enumeration on small graphs and generated graphs, verify every arc meets constraints, test directed/parallel/equal-cost paths, disconnected graphs, same-node routes, invalid nodes, unknown values, boundaries, stale data, closures, geometry order, and all alternatives. Invalid zero/negative/NaN edges are rejected (zero-cost graph edges are not supported). Every admissibility condition above is a test invariant. Phase 0 fixture checks do not satisfy these implementation gates.
