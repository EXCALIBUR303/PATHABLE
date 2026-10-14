# Testing conventions and acceptance evidence

## Current executable checks

Current readiness through Phase 8 independent final audit, from repository root:

```sh
bash scripts/test.sh
bash scripts/test_frontend.sh
.venv/bin/python scripts/smoke_api.py
.venv/bin/python scripts/smoke_routes.py
.venv/bin/python scripts/smoke_frontend.py
.venv/bin/python scripts/smoke_events.py
.venv/bin/python scripts/smoke_ml.py
```

Restart persistence is `.venv/bin/python scripts/verify_persistence.py`; run it separately from database tests because it restarts the shared DB. [Phase 1 evidence](PHASE1_TEST_EVIDENCE.md), [Phase 2 evidence](PHASE2_TEST_EVIDENCE.md) [Phase 3 evidence](PHASE3_TEST_EVIDENCE.md) and [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md) record actual results separately. Backend and browser fixtures independently migrate fresh UUID-named databases and protect development data. Browser tests use dedicated ports, an isolated optimizer cache and a test-only administrator; graceful teardown drops only their disposable database. See [development setup](DEVELOPMENT.md) for Chromium prerequisites.

Historical Phase 0 command (documentation-only scaffold check, not current application readiness):

```sh
python3 scripts/validate_phase0.py
git diff --check
```

The Python command uses only the standard library. It checks files/links/scaffold and token contrasts, enumerates all simple paths in a tiny synthetic **design fixture**, verifies expected costs and exclusions, and checks lower-bound inequalities. It deliberately does not implement Dijkstra, A*, an API or a database. These results cannot be counted as production routing tests. Actual evidence is in [TEST_EVIDENCE.md](TEST_EVIDENCE.md).

## Test boundaries

Backend unit tests live in `backend/app/tests/unit/`, API/integration in `backend/app/tests/integration/`, pure routing tests in `backend/app/tests/routing/`. Use pytest with real PostgreSQL/PostGIS integration fixtures, database-per-worker isolation or explicit transactional cleanup; never point tests at a user's database. Frontend Vitest/Testing Library tests are colocated with features. Playwright tests live in `frontend/e2e/` and use real seeded API/DB services for end-to-end acceptance. Mocks are limited to isolated components/fault injection and clearly identified.

Phase 1's backend commands and Phase 2's frontend type/lint/format/component/build/browser scripts now exist and have executed. The wrapper runs generated OpenAPI drift checks before frontend validation. Phase 3 pure-routing, route API/concurrency and route browser tests now execute. Report/evidence/SSE/analytics tests now execute; Phase 5 private-job/review and optional CPU fixture tests now execute; do not count missing placeholders as passing checks. Use fixed seeds for randomized tests and retain failing graph fixtures with provenance.

## Mandatory critical tests

| ID | Scenario and required assertion | Phase / current status |
| --- | --- | --- |
| A | Shortest unconstrained route uses stairs; avoid_stairs result has none and is optimal within admissible graph | P3 / verified: independent oracle, API and stairs-toggle browser |
| B | Verify an obstacle on chosen route; committed graph revision changes; client invalidates and computes an admissible alternative | P4 / verified: real report/private image → verified restriction → SSE retirement → confirmed admissible reroute |
| C | Every admissible connection removed; API no_route and UI honest unavailable state; no fabricated line | P3 / verified: disconnected/constraints API and no-overlay browser |
| D | Same snapshot/profile/cost: Dijkstra and A* equal optimal cost within max(1e-6,1e-9 relative); each also agrees with independent oracle | P3 / verified: 163 pure tests include generated/oracle and ECEF invariants; live algorithms agree |
| E | Ordinary user cannot review reports; endpoint returns 403, no DB/audit/restriction changes | P4 / verified: forbidden review and fresh role revocation cause no mutation |
| F | Unreviewed or accepted AI prediction alone leaves restrictions and graph_version unchanged | P5 / verified with marked synthetic prediction doubles through real DB/API/browser; no trained hazard claim |
| G | Unknown/unverified/stale facts are excluded when needed by hard limits; permissive route carries uncertainty, never verified-safe label | P3 / verified: unknown/stale hard filtering, permissive warnings and length-weighted coverage; P4 unreviewed reports have no graph effect |
| H | Persist user/profile/infrastructure; restart API and DB container retaining named volume; same records still exist | P1/P6 / retained-volume restart evidence |
| I | Frontend route geometry, distance, ETA, warning and chosen alternative correspond to actual backend response | P3 / verified: real API totals/instructions/warnings/alternative browser plus exact map-boundary geometry component tests |
| J | Fake MIME, SVG, excessive bytes/pixels, malformed images and path traversal rejected; no public file or unauthorized evidence access | P4 / verified: actual worker byte/pixel/MIME/privacy/path checks and private owner/admin access |
| K | Two concurrent reviews and repeated requests cannot duplicate or conflict; resolution of one report cannot release another's restriction | P4 / verified: independent concurrent reviews/replays, stale browser CAS and source-specific resolution |
| L | After graph/expiry mutation, old cache/snapshot is not returned as current; no-cache path validated now, cache adapter tested if introduced | P3 / verified: no-cache revision/expiry/retry/currentness; P4 replay/reset/offline/resume/cancellation verified; cache adapter remains unnecessary because no cache exists |

## Additional correctness checks

- Graph: directed/parallel arcs, reverse geometry, geometry endpoints, WGS84 units, invalid/self-loop/zero/negative/nonfinite edges, disconnected components, same-node Point, exact constraint boundaries, equal-cost paths, every alternative and primary optimality.
- Freshness: inject database clock; expire an observation between snapshot load and response, verify bounded retry/event/CAS, keep shared model/policy/version identities consistent.
- Transactions: independent DB sessions, synchronize conflicting writes with barriers, test idempotency payload mismatch, rollback after each step and graph event replay after lost notification.
- Auth: session rotation/expiry/revocation, anonymous CSRF, exact origins, role mass assignment, ownership, inactive user, bounded hashing/rate limits and trusted proxy configuration.
- UI: keyboard-first search/forms, loading/empty/error/success, stale responses, duplicate/gapped events, offline/resume, text alternatives for map/charts, reduced motion and focus management.
- ML: real decoder validation, preprocessing reproducibility, job retry/idempotency, actual model asset compatibility and metrics if resources exist; unavailable mode remains separately tested.

## Evidence discipline and performance

Capture exact command, working directory, revision or uncommitted state, runtime versions, actual test count, exit code, pass/fail/skip/xfail and logs/results from that run. Preserve the command's exit status with pipefail when piping. A zero-test run is not a pass. Do not turn required tests off to get green output. Each phase updates status and evidence; diagnose setup failures separately from product bugs.

Initial measurement targets, **not guarantees**: representative 2k-node/5k-physical-edge graph; P95 primary calculation <=500ms and up to two alternatives <=1.5s on documented CPU; event-to-client stale indication <=2s while connected. Load tests must record hardware, concurrency, graph/profile distribution and time budget. Correctness and hard constraints take priority over these targets. New benchmark failures guide profiling, not arbitrary complexity.

Browser auto-fixtures reset only the UUID-generated test database rate buckets between independent scenarios, and use a separate private upload directory. Actual hourly limits and Retry-After are covered separately by controlled database-clock tests; production quotas are not disabled. Final Phase 4 counts are 303 backend, 38 component and 18 browser tests with no failures/skips/retries. Critical F now passes in Phase 5 integration; whole-system release audits remain unrun.

Phase 5 final checks: 320 backend tests, 41 component tests and 19 browser tests. `bash scripts/test_ml.sh` separately runs ten actual CPU serialization/training/evaluation/inference checks on seeded synthetic fixtures; those are not real hazard metrics. Worker permission/lease/output/CAS tests use disposable DBs and a separately dropped test role. See [Phase 5 evidence](PHASE5_TEST_EVIDENCE.md). Genuine trained-model evaluation remains unrun because licensed data/evaluated weights are absent.

Phase 6 final results: **330 backend**, **41 component**, **22 browser** and **10 separate synthetic CPU pipeline** tests pass. Browser axe rules cover public/private/admin/review states without exclusions, with public reflow at 320 CSS pixels; keyboard focus/reduced-motion cases also pass. Security regressions cover fresh graph/evidence authorization, malformed CSRF, error headers and fail-closed authenticated writes during a DB outage. The real proxy/browser scenario covers ownership, roles, CSRF, cookie flags, text escaping and logout. Initial failures, exact final commands, advisory scope, benchmark target miss and release limitations are recorded in [Phase 6 evidence](PHASE6_TEST_EVIDENCE.md).

Phase 7 final application checks pass: **332 backend**, **41 component**, **22 browser** and **10 CPU pipeline** tests. `bash scripts/test_release.sh` additionally passes eight-helper Ruff/format, six backup-manifest unit tests, verified offline builds, strict HTTPS and built-browser account/route flows, coordinated real private-image restore/restart/refusal checks, and a clean no-cache source export. This exposed a production-only Leaflet class bug hidden by development Strict Mode; its initial-layer options and component mock were repaired and production regression passed. Hosted CI and remote clone/cloud restoration remain unrun. Exact failures/resource corrections and final results are in [Phase 7 evidence](PHASE7_TEST_EVIDENCE.md).

Phase 8 final results: **341 backend**, **41 component**, **22 browser**, **10 CPU fixture** and **22 operator-helper** tests pass, with no final failures/skips/retries. The full release wrapper passes rebuilt HTTPS/production-browser, actual private-image/database recovery/restart, occupied-target refusal and clean-source no-cache checks. Nine new backend regressions cover malformed cursors, unexpected-error rollback/headers and distinct role names. Recovery checks reject incomplete metadata before contacting the target and protect runtime ownership. Four helper regressions reproduce a transient pre-exec identity and verify that mismatched processes are never signaled. Real owned-service restart/repeat startup also passes. A separate real container probe verifies root-operated staging is readable by the configured non-root identity. The [final audit](FINAL_ENGINEERING_AUDIT.md) records exact commands, observed limits and all 20 final criteria.
