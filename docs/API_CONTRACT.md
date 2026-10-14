# API contract

Contract v1; Phase 1, 3, 4 and 5 integration endpoints are implemented and tested: 47 operations across 43 paths. [Generated OpenAPI](openapi.json) is exported from FastAPI/Pydantic and consumed by generated frontend TypeScript types with a drift check. Trained hazard inference remains unavailable without approved evaluated assets. Base path `/api/v1`; JSON uses snake_case, UUID strings, RFC3339 UTC timestamps, and decimal-string bigint versions. Longitude precedes latitude in all GeoJSON.

## Common behavior

Resource responses are direct JSON objects, not a second `data` envelope. Collections use `{items, next_cursor}`; opaque cursor pagination defaults to 25 and caps at 100 with stable `(created_at,id)` ordering. Locations may sort by `(name,id)`. Reject extra write fields, invalid finite numbers, unknown enums, oversized inputs, and mass-assigned server fields. Request bodies <=64 KiB except multipart evidence uploads. Scope campus resources explicitly.

Error format: `application/problem+json` with `type`, `title`, `status`, `code`, `detail`, `request_id`, and optional `field_errors`, integer `current_version` for resource CAS, or decimal-string `current_graph_version` for routing races. No stack traces, SQL, credentials, or private resource existence leaks. Use 400 malformed JSON/cursor; 401 unauthenticated; 403 authenticated but forbidden/CSRF; 404 absent or not owned; 409 stale version, idempotency conflict, or rapidly changing graph; 413 excessive bytes; 415 unsupported media; 422 validation/transition/graph association error; 429 rate limit with Retry-After; 503 unavailable dependency/budget. No-route is a valid domain result (200), not an HTTP/server error.

Authentication is the opaque HttpOnly session cookie from [security](SECURITY.md). State-changing mutations require `X-CSRF-Token` and exact allowed Origin checks. The public read-only routing POST is an explicit exception: no account state or route history is written, and the existing durable 60/minute identity/IP quota applies. Public read/map/route APIs need no login; reports, preferences and saved destinations do. No endpoint trusts a client-supplied user/reviewer/role. Admin writes also require `expected_version` and `reason`. Resource mutations return the new row_version. Version mismatch returns 409 and current_version; never silently last-write-wins. Retried report creation and admin review/resolution require a UUID `Idempotency-Key`; replay returns the original authorized result for 24h, even if the resource has since changed. Clients then fetch current state. Different body with the same key is 409.

## Endpoint inventory

`Public` means callable without an authenticated user, with normal validation/rate limits. `Owner` means authenticated and scoped to the current user. P denotes implementing phase.

| Method and path | Access | Request → success | P |
| --- | --- | --- | --- |
| GET /health/live | Public | Process liveness only → 200 `{status:"alive"}` | 1 |
| GET /health/ready | Public | DB query + PostGIS + expected migration → 200 `{status:"ready"}` or 503 | 1 |
| GET /auth/session | Public | Set anonymous session when absent; return `{user:null\|User, csrf_token, expires_at}`; Cache-Control no-store | 1 |
| POST /auth/register | Public + CSRF | `{email,password,display_name}` → 201 User; no automatic admin; duplicate email 409 | 1 |
| POST /auth/login | Public + CSRF | `{email,password}` → 200 session view + rotated cookie/CSRF; generic credential failure | 1 |
| POST /auth/logout | Session + CSRF | Revoke current session, clear cookie → 204; repeated logout safe | 1 |
| GET /me | Owner | → User including role, no password/session internals | 1 |
| PATCH /me | Owner | `{display_name,expected_version}` → User | 1 |
| GET /me/accessibility-profile | Owner | → complete Profile; create conservative profile at registration | 1 |
| PUT /me/accessibility-profile | Owner | complete Profile + expected_version → Profile | 1 |
| GET /me/saved-destinations | Owner | → paginated SavedDestination | 1 |
| POST /me/saved-destinations | Owner | `{location_id,label?}` → 201; duplicate 409 | 1 |
| DELETE /me/saved-destinations/{id} | Owner | → 204 | 1 |
| GET /campuses | Public | → campuses with data_origin and attribution | 1 |
| GET /locations?campus_id=&q=&cursor= | Public | q <=100 chars → list including access_points with node IDs | 1 |
| GET /locations/{id} | Public | → Location and selectable access points | 1 |
| GET /infrastructure?campus_id=&bbox=&cursor= | Public | bbox west,south,east,north validated → list including status/provenance | 1 |
| GET /infrastructure/{id} | Public | → Infrastructure, linked edge IDs, public verification metadata | 1 |
| GET /campuses/{id}/graph | Public | bounded GeoJSON FeatureCollection of active nodes/edges, version, valid_until, data_origin; reject excessive campus size with pagination/export guidance | 1 |
| GET /campuses/{id}/graph-version | Public | `{graph_version,validated_at,valid_until,data_origin}` after freshness maintenance | 1 |
| POST /admin/locations | Admin | campus/name/kind/point + reason → 201 Location | 1 |
| PATCH /admin/locations/{id} | Admin | allowlisted fields/access_points + expected_version + reason → Location; validate same-campus node mappings | 1 |
| POST /admin/path-nodes | Admin | campus/name/point/level + reason → 201 Node; graph transaction | 1 |
| PATCH /admin/path-nodes/{id} | Admin | expected_version + reason + fields; moving point requires incident geometries atomically → Node | 1 |
| POST /admin/infrastructure | Admin | campus/location/kind/point/observations/edge_ids + reason → 201 Infrastructure | 1 |
| PATCH /admin/infrastructure/{id} | Admin | allowlisted descriptive/status fields + expected_version + reason → resource; version/event/audit transaction | 1 |
| POST /admin/path-edges | Admin | campus, endpoints, geometry and measured observations + reason → 201; derived distance only on server | 1 |
| PATCH /admin/path-edges/{id} | Admin | measured/baseline fields, expected_version, reason → resource; no raw distance/version override | 1 |
| POST /admin/path-edges/{id}/retire | Admin | expected_version, reason → resource (soft retirement, preserve historical references) | 1 |
| POST /routes/calculate | Public | RouteRequest → RouteResult union below | 3 |
| POST /reports | Owner | ReportCreate + Idempotency-Key → 201 Report, status pending_review | 4 |
| GET /reports | Owner | own reports; optional status/campus/cursor → collection | 4 |
| GET /reports/{id} | Owner or Admin | → Report with history/evidence metadata; other users 404 | 4 |
| POST /reports/{id}/evidence | Owner | multipart `file` and integer `expected_version`, pending report only → 201 Evidence or explicit rejection; per-report cap enforced transactionally | 4 |
| GET /reports/{id}/evidence/{evidence_id}/content | Owner or Admin | authorized ready image stream; private/no-store | 4 |
| DELETE /reports/{id}/evidence/{evidence_id} | Owner | pending report only + expected_version → 204; verified evidence retained per policy | 4 |
| GET /admin/reports | Admin | status/category/campus/date/cursor → review queue | 4 |
| POST /admin/reports/{id}/review | Admin | decision verify/reject, confirmed_edge_ids, restriction_kind, reason, expected_version + key → Report | 4 |
| POST /admin/reports/{id}/resolve | Admin | expected_version, reason + key → resolved Report; release only this report's restrictions | 4 |
| GET /admin/audit | Admin | required campus_id and limit/cursor → audit history | 4 |
| GET /admin/analytics?campus_id=&from=&to= | Admin | defined aggregate payload below | 4 |
| GET /campuses/{id}/events | Public | SSE, Last-Event-ID decimal version, replay/reset protocol | 4 |
| GET /ml/status | Public | `{available,reason,model_version_id,model_name}`; disabled is 200 available=false | 5 |
| POST /reports/{id}/inference | Owner or Admin | ready evidence_id + key → 202 Job; no evaluated weights → 503 ML_UNAVAILABLE | 5 |
| GET /reports/{id}/inference/{job_id} | Owner or Admin | private persisted job status/errors/source/model identity → Job | 5 |
| GET /reports/{id}/predictions | Owner or Admin | persisted predictions with provenance → collection | 5 |
| POST /admin/predictions/{id}/review | Admin | decision accept/reject + reason + expected_version + Idempotency-Key → annotation; **no route mutation** | 5 |

Phase 1 must create graph update/version primitives for infrastructure writes. Phase 4 adds reporting and live SSE delivery atop them; it must not invent a conflicting second graph-version mechanism. Before a phase exists, frontend interfaces show unavailable states; do not return successful fake responses. Health paths above are relative to `/api/v1`.

## Value objects

User: `{id,email,display_name,role,row_version}`. Email <=254 characters, normalized before uniqueness; password 12–128 characters, allow paste/password managers, no forced arbitrary character categories. Display name 1–80 characters after trim. Profile:

```json
{
  "avoid_stairs": true,
  "max_slope_pct": 8,
  "min_width_m": 0.9,
  "excluded_surfaces": ["uneven", "gravel"],
  "unknown_policy": "exclude",
  "travel_speed_mps": 1.0
}
```

Slope range [0,100] or null; width (0,10] or null; speed [0.1,3]. Do not encode wheelchair status or diagnosis; a UI preset expands to explicit values. Version belongs to the persisted Profile wrapper, not the computational value.

ReportCreate: `{campus_id,category,description,point,location_id?,infrastructure_id?,suggested_edge_ids:[]}`; point is GeoJSON Point within the supported campus. Categories: `blocked_ramp`, `inaccessible_entrance`, `damaged_pathway`, `elevator_unavailable`, `temporary_obstacle`, `other_accessibility_concern`. Suggested edges must belong to the same campus; they do not change availability. Description 10–2000 characters. Reviewer assignment and status are server-owned. Report includes reporter-visible review history, row_version, evidence states, and synthetic origin. Public map obstacles expose confirmed restrictions without reporter identity or private evidence.

## Routing contract

RouteRequest: `{campus_id,source_id,destination_id,accessibility_profile,selected_algorithm,alternatives_limit}`. Algorithm `dijkstra` or `astar`; default astar; alternatives_limit counts **additional** routes, integer 0–2. Accessibility profile is explicit and complete; backend independently validates it. Frontend may fill it from a saved profile or a conservative guest preset before submitting. No credential needed for a calculation.

Profile fingerprint: SHA-256 of RFC 8785 canonical JSON of the complete validated profile, with excluded_surfaces deduplicated and sorted. Equivalent numeric encodings (1 and 1.0) and surface-list ordering must not change identity. The server computes and returns it; clients use the returned value rather than inventing a second hashing scheme. Phase 3 tests verify this normalization, including negative zero and equivalent numeric encodings.

Found result shape:

```text
status: "found"
source_id, destination_id, campus_id
graph_version, policy_version, cost_model_version, profile_fingerprint
validated_at, valid_until: timestamp | null
data_origin: "synthetic_demo" | "surveyed"
algorithm: "dijkstra" | "astar"
accessibility_profile: Profile
primary: Route
alternatives: Route[]
alternatives_exhaustive: boolean
excluded_edge_counts: Record<string, number>
stats: {expansions, searches, elapsed_ms, alternative_candidates}
warnings: Warning[]
```

Route: `{node_ids, arcs:[{edge_id,direction}], geometry, total_distance_m, estimated_duration_s, cost_m_equivalent, instructions, verification, warnings}`. Direction is forward/reverse. Geometry is LineString for >=1 arc, Point for same-node routes. Instructions reference traversed edge IDs and distances; they must reconcile with totals. Verification includes verified/current physical distance, unknown/needs-review distance, earliest observation expiry, and wording `observations_current` / `contains_uncertainty`; never `safe`. Warning: `{code,message,edge_ids}` with enumerated codes, e.g. `UNKNOWN_ACCESSIBILITY`, `UNVERIFIED_OBSERVATION`, `DURATION_ESTIMATE`, `SYNTHETIC_DATA`. Verification coverage is length-weighted over traversed arcs, not graph-wide labels. Every alternative uses identical graph/profile/cost identity. Top-level warnings apply to the entire result (synthetic data and estimated duration); each route carries its own uncertainty warnings, so choosing an alternative does not change the primary's observation label. Instruction fields are `{edge_id,distance_m,text,maneuver,node_id,slope_pct}`, with signed slope in travel direction.

No-route result repeats snapshot/profile/source/campus fields and sets `status:"no_route"`, `reason`, `excluded_edge_counts`, `warnings`, `primary:null`, `alternatives:[]`. Count physical edges once per exclusion reason; one edge may contribute to multiple reasons, so totals are not additive. It contains no invented total_distance_m or geometry. Returning a route found only after ignoring restrictions is forbidden. See [design fixtures](examples/README.md) for small, internally checkable scenarios; actual UUID/time, geometry, warning and totals assertions execute in the Phase 3 API/browser tests.

Graph update race: 409 `GRAPH_CHANGED_RETRY`; dependency outage: 503 `DATABASE_UNAVAILABLE`; invalid stored graph: 503 `GRAPH_INVALID`; algorithm timeout: 503 `ROUTING_BUDGET_EXCEEDED`. No UI fallback route on these errors. Optional `expected_graph_version` in future versions must not force use of a stale graph. Snapshot validation retries once before a 409. Known campus with missing graph metadata returns 503; an unknown campus/node is 404; cross-campus endpoints are 422.

The adapter preflights at most 10,000 rows per graph collection, 100,000 dependencies and 100,000 geometry points in one repeatable-read snapshot, with at most 1,000 points per physical edge. Oversize/malformed stored graph returns 503. Searches share a 100,000-expansion/two-second budget. Primary exhaustion is a 503, never no-route. Secondary exhaustion preserves the proven primary with `alternatives_exhaustive:false`; candidate count is capped at 20. Returning the requested number of alternatives completes that request without claiming enumeration of every possible route. The current frontend uses durable SSE plus ten-second version polling and focus/visibility/offline/expiry checks; every known new revision retires guidance and live recalculation requires confirmation.

## Analytics definitions

Filters: campus_id required; from inclusive, to exclusive UTC timestamps, maximum 366 days. Stock metrics are explicitly `as_of` current snapshot; flow metrics use the requested window. Return denominator, null for division by zero, and data_origin on every dashboard response. No synthetic hardcoded counters.

| Metric | Grain and exact definition |
| --- | --- |
| mapped_infrastructure_count | Active infrastructure rows in campus (stock) |
| verified_accessible_pathways | Distinct active physical edges labeled accessible with current verification; does not claim availability or suitability for every profile |
| unknown_accessibility_pathways | Distinct active physical edges whose accessibility is unknown; separately report needs_review/unverified counts, which can overlap |
| active_verified_obstacles | Verified unresolved reports with >=1 active restriction (stock), counted once per report |
| pending_reports | Current pending_review reports (stock) |
| category_distribution | Reports submitted in [from,to), grouped by category; explicit total |
| resolution_trend | Resolved report count grouped by resolved_at UTC day within window |
| average_resolution_seconds | Mean resolved_at minus created_at for reports resolved in window; return count and null when none |
| accessibility_mapping_coverage | Length of active physical edges with known accessibility AND current verification divided by all active physical-edge length; denominator is mapped network only, not entire real campus; label as such |

Pathway length counts physical edges once, never both directed arcs. Availability is a separate metric. Provide tabular equivalents for charts. SQL aggregation tests must include empty datasets, joins with multiple evidence rows, overlapping reports, excluded boundary dates, and denominator zero.

## Implemented reporting and streaming details

ReportCreate accepts campus_id, category, description (10–2000 characters), WGS84 Point inside the supported campus, optional location_id/infrastructure_id and up to 50 unique suggested_edge_ids. Categories: blocked_ramp, inaccessible_entrance, damaged_pathway, elevator_unavailable, temporary_obstacle, other_accessibility_concern. All associations must be active and same-campus. Suggestions never restrict routes. Report responses include provenance, immutable submitted content, row_version/timestamps, status/reviewer/resolution metadata, suggested/confirmed physical-edge IDs, append-only history and evidence metadata. Private storage keys/uploader internals are absent from evidence responses.

Verification/rejection accepts decision, expected_version, reason, up to 50 confirmed_edge_ids and restriction_kind (closed or temporarily_blocked). Verification with an empty selection may use the report's mapped infrastructure; a missing real edge mapping is 422. Rejection cannot supply restricted edges. Resolution is expected_version/reason. Both require a UUID Idempotency-Key. Fresh role/auth-version checks occur inside the domain transaction, including authorized replays. Pending/rejected/resolved reports have no active source restrictions; verified reports have at least one. Verification while evidence is processing returns 409.

Evidence POST has multipart/form-data with exactly one file and one expected_version field. Do not manually set the boundary in browser code. JPEG/PNG only, encoded file <=10 MiB, full multipart <=10 MiB+64 KiB, decoded pixels <=20M, at most three active slots/report and 100 MiB/user storage. Actual streaming bytes are enforced independently of Content-Length. Ready output is normalized and metadata-free. GET content returns binary image/jpeg or image/png with private/no-store; DELETE takes JSON expected_version and returns 204. Upload/deletion change the pending report version and are not Idempotency-Key operations. Quota responses use Retry-After for the actual remaining fixed bucket window.

GET /admin/analytics requires campus_id and timezone-aware `from`/`to` timestamps; response uses from_time/to_time/as_of, counts and category_distribution/resolution_trend arrays, submitted_report_count/resolved_report_count, average_resolution_seconds, mapping_known_current_length_m, mapping_total_length_m and nullable accessibility_mapping_coverage. GET /admin/audit requires campus_id with limit/cursor; its allowlisted metadata includes actor, reason, request ID and nullable graph version. Audit/evidence are never public stream payloads.

GET /campuses/{id}/events returns text/event-stream, optional cookie identity and Last-Event-ID decimal version (header <=100 characters). IDs are campus revisions, with graph.updated or graph.reset and only curated campus/version/changed-edge/reason/time fields; large change lists set changes_truncated. Replay batches are <=100 revisions, changed IDs <=200, heartbeat comments every 15 seconds and immediate on an empty initial replay. Invalid/missing/future/expired/gapped cursors reset. Stream errors are generic stream.error frames; clients reconnect and revalidate current metadata. Three leases/identity, 200 global, 45-second expiry; public frames never expose report descriptions, identity or images.

## Optional ML integration (Phase 5)

GET /ml/status returns available, reason, nullable model_version_id/model_name. DISABLED, EVALUATED_MODEL_MISSING, ML_RUNTIME_MISSING, ML_WORKER_NOT_CONFIGURED or MODEL_ASSETS_INVALID are honest unavailable states. READY means an approved immutable bundle and worker configuration can accept work; it is not a worker heartbeat/capacity promise. No dataset/model is installed or enabled for product use here.

POST /reports/{id}/inference accepts only evidence_id plus UUID Idempotency-Key; authorization/CSRF precede the ready-image/model checks. Missing resources return 503 ML_UNAVAILABLE without a successful job. Accepted jobs return 202 with immutable report/evidence/model/hash identity, queued/running/succeeded/failed/unavailable status, attempts, typed error_code, optional latency_ms/abstained and timestamps. Submission is 20/hour/user; global pending/running queue is capped at 100. Replays are authorized, and a different key still reuses the unique evidence/model job. Terminal jobs are not implicitly restarted.

GET predictions is owner/admin scoped and paginated. Each classification observation has source job/evidence/model/name, class_name, model score, null box_xyxy, abstention, status/review metadata, row_version and test_fixture marker. Synthetic test models cannot be activated; the visible marker prevents fixtures being mistaken for real predictions. Scores are uncalibrated model outputs, not safety probabilities.

Admin review is expected_version/decision/reason/idempotency-controlled. A successful accept/reject appends audit with null graph_version, increments only the prediction version and cannot verify a report, add restrictions or advance graph state. A separate authorized report verification is still required. Reviewed annotations are final. Expired worker leases cannot publish, and evidence deletion serializes with final output publication through the common content advisory lock. Core routing/reporting never imports tensor dependencies.
