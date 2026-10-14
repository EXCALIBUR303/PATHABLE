# Phase 3 implementation and validation evidence

Completed 2026-10-13 in `/workspace/PATHABLE`, locally saved/uncommitted on unborn branch `work`. No commit, push, deployment or environment publication. Requested phase setting: GPT-6 Astra / Max; actual runtime model/effort is not independently exposed. This evidence covers routing and its existing administration precursor, not Phase 4 reports/SSE or later ML/release work.

## Runtime and scope

Python 3.12.14, pytest 9.1.1, Node 24.19.0, npm 11.9.0, system Chromium 154.0.8037.57 with locked Playwright 1.64.0, Vite 8.3.4, React 19.3.0, TypeScript 5.9.3, Vitest 5.0.4. Existing digest-pinned PostgreSQL 17.5/PostGIS 3.5 runs through Compose. RFC 8785 canonicalization adds hash-locked `rfc8785==0.1.4`; frozen Python/npm installation and `pip check` pass without peer/verification overrides.

The pure engine uses only the standard library and immutable input values. HTTP/schema, canonicalization and database operations remain in adapters. Route API, exact generated OpenAPI/TypeScript contract and frontend are implemented. Generated API now has 30 operations across 27 paths. See [ADR-012](adr/012-phase3-routing.md) and [routing design](ROUTING_DESIGN.md).

## Final commands and observed outcomes

Unless noted, working directory is the repository root. All final commands below exited 0. Final runners reported no failures, skips, expected failures or disabled tests; browser retries are disabled.

| Command | Actual result |
| --- | --- |
| `bash scripts/test.sh` | Ruff passed; 34 backend/migration files formatted; **242 pytest tests passed in 22.21s**. Breakdown: 163 pure-routing, 42 routing integration, 37 existing backend/CLI. One Starlette/httpx test-client deprecation warning. |
| `bash scripts/test_frontend.sh` | Generated OpenAPI/type drift check, strict TypeScript, ESLint and Prettier passed; **22 Vitest tests across seven files passed in 3.43s**; production build passed (2,900 modules, 582ms reported Vite build); **12 Playwright tests passed in 51.7s** against real disposable PostGIS/API/UI. |
| `.venv/bin/python -m pytest -c backend/pyproject.toml backend/app/tests/routing` | **163 passed** independently from the repository root; pure fixtures override DB creation/reset. |
| `bash scripts/install.sh` | Python `--require-hashes` install and `npm ci` (378 packages) passed; healthy DB, migration/runtime grants and existing synthetic campus preserved. |
| `.venv/bin/python scripts/dev.py stop && .venv/bin/python scripts/web.py stop && bash scripts/start.sh` | Only owned API/UI stopped and restarted. DB readiness/migrations, preserve-existing seed and API, dual-algorithm routing, compiled frontend/proxy smoke passed. |
| `.venv/bin/python -m pip check` | No broken requirements; a nonfatal unwritable default pip-cache warning occurred. Installation uses the repository's writable cache. |
| `.venv/bin/ruff check scripts/smoke_routes.py scripts/benchmark_routing.py` and matching `ruff format --check` | Both new helpers passed. |
| `bash -n scripts/install.sh scripts/start.sh scripts/test.sh scripts/test_frontend.sh` | Shell syntax passed. |
| `.venv/bin/python scripts/benchmark_routing.py` | 20 deterministic pure-engine calculations completed with matching primary cost across algorithms; timing and incomplete alternatives recorded below. |

A read-only owner connection to `postgres` queried `pg_database`: **zero** remaining `pathable_e2e_*` or `pathable_test_*` databases after final teardown. Test fixtures did not truncate the development DB. Current-instance logs are `/tmp/pathable-phase3-backend.log`, `/tmp/pathable-phase3-frontend-final.log`, `/tmp/pathable-phase3-install.log`, `/tmp/pathable-phase3-start.log` and `/tmp/pathable-phase3-benchmark.log`; temporary logs are not durable repository artifacts.

Final repository inspection checked **84 local Markdown links** and source whitespace across **180 nonignored files**, parsed the recorded benchmark JSON, and passed `git diff --check`. Because the branch is unborn and files are untracked, the explicit file scan supplements Git's diff check. `npx prettier --check README.md` from `frontend/` passed after documentation updates. Git ignore checks confirm private `.env`, environments/dependencies and local screenshot artifacts remain excluded.

## Correctness and live behavior

- **A/D:** Fixed-seed directed multigraphs compare Dijkstra and A* independently to exhaustive simple-path enumeration, including parallel/equal-cost paths and improvements smaller than reporting tolerance. Tests verify ECEF consistency/admissibility, dateline/polar handling and distance lower bounds. API/browser compare algorithms and show that avoiding stairs excludes the shorter stairs path.
- **C/G:** Exact slope/width/surface/stair boundaries, nullable/unverified/expired facts, permissive uncertainty without relaxing hard constraints, both directions of mapped closures and inactive dependencies are tested. Disconnected/constraint-excluded routes remain 200 domain results; corrupt graph/primary budget failure remain errors. No fallback route is invented. Physical-edge exclusions and length-weighted verification are checked.
- **Alternatives:** Same filtered graph, loopless arcs, cost stretch and pairwise physical-distance overlap limits; rejected candidates do not lose their Yen partitions. Limits/exhaustion are explicit; primary remains optimal. Same-node returns one Point, zero distance/effort/time and no instructions; missing/cross-campus IDs have distinct errors.
- **Snapshot/B/L precursor:** Real read-only repeatable-read transactions retain one revision despite concurrent writes. Freshness maintenance and final lock/expiry validation rebuild once; a second race returns 409. Observation expiry, graph-size preflight, missing metadata, canonical fingerprint normalization and ten synchronized concurrent requests are covered. No route-result cache exists.
- **I:** Live browser assertions compare selected primary/alternative distance, rounded duration, backend instruction text, observation status and warnings to actual HTTP responses. Map adapter component tests preserve every ordered backend vertex when converting longitude/latitude for Leaflet, switch alternative geometry and remove retired geometry; a same-node Point produces no line. Browser tests render the real Leaflet SVG and alternative dash style.
- **Client races/currentness:** Five hook tests cover A→B→A result retirement, late response despite abort, monotonic expiry with a years-behind device clock, changed/failed version confirmation without automatic route retry, and service-error/no-route separation. Browser tests close a real mapped ramp through the authorized API, wait for polling invalidation, remove the old line, then recalculate on the newer revision avoiding its physical edges.
- **Existing features:** Final browser suite retains real account/profile/saved-place persistence, session logout, ordinary-user/admin boundaries, keyboard search, error recovery, mobile/reduced-motion navigation and honest unsaved reporting draft checks.

Screenshots `.local/screenshots/phase3-route.png` (desktop 1440px) and `phase3-mobile-route.png` (390px) were viewed. Selected routes, alternative controls, text directions, measured totals, warnings and synthetic provenance are visible. The mobile browser asserts no horizontal overflow. Screenshots stay ignored; they are not published. This establishes those workflows, not WCAG conformance.

## Measured workload and limits

[Recorded benchmark JSON](examples/phase3-benchmark.json) contains all 20 samples, measured at 2026-10-13 04:15:14 UTC. Deterministic synthetic grid: 2,000 nodes, 5,000 physical edges, 10,000 directed arcs, five origin/destination pairs per algorithm/alternative setting, sequential requests. Includes graph validation, filtering and search; excludes database, HTTP and frontend. Host: Linux x86_64/glibc 2.41, Intel Xeon Platinum 8573C; Python reports five logical CPUs. Shared-host scheduling was not isolated.

| Algorithm | Additional routes requested | Median ms | P95 nearest-rank ms (five samples) | Incomplete secondary searches |
| --- | ---: | ---: | ---: | ---: |
| Dijkstra | 0 | 114.62 | 206.49 | 0/5 |
| A* | 0 | 78.95 | 219.42 | 0/5 |
| Dijkstra | 2 | 440.52 | 632.38 | 5/5 |
| A* | 2 | 585.57 | 881.99 | 5/5 |

Primary times are below the initial 500ms target and bounded alternative times below 1.5s in this sample. Five samples make P95 the maximum, not a robust production percentile. All ten alternative runs exhausted a configured secondary-search limit and marked `alternatives_exhaustive:false`; these timings do **not** demonstrate complete alternative enumeration. The valid primary is retained. The default combined budget is 100,000 expansions/two seconds and at most 20 additional candidates. Increasing limits requires new evidence rather than relaxing constraints. There is no concurrent throughput, HTTP/DB P95 or production-capacity claim.

## Repairs, limitations and setup persistence

Implementation validation corrected optional-auth connection retention before independent snapshot sessions, global warnings that could attribute an alternative's uncertainty to the primary, frontend stale-response/input/expiry handling, explicit empty-entrance selection, and geometry-transfer preflight. After the warning contract correction, an integration assertion still expected the old global warning placement: that intermediate run had **241 passed, one failed**. The assertion was changed to require per-route uncertainty and only global synthetic/duration warnings; the final **242-test run passed**. An oversized-geometry fixture initially violated the existing PostGIS length invariant; it was replaced with a nondegenerate valid geometry to exercise the intended point-limit guard. No assertions were disabled or production constraints weakened. Earlier targeted checks are not added to final test totals.

The reusable cloud `install_script` and complete Phase 3 `start_skill` were saved successfully (`status=saved`, `requires_publish=true`) after their install/start commands ran. The update preserved repository, network and secret settings. The draft explains retained dependencies versus restarted DB/API/UI, safe shutdown, functional route smoke, isolated tests and benchmark limitations. Review/save it in environment settings, then publish; saving did not apply/publish a snapshot. Fresh-task file restoration, Docker-volume snapshot restoration, macOS and bundled Chromium download remain unverified. Phase 1 retained-volume restart evidence is historical, not rerun here.

Ten-second version polling can discover external edits up to one interval later; SSE replay and the two-second event target belong to Phase 4. Reports/uploads/review ledgers/analytics and ML remain unavailable. Full accessibility audit, other browsers, real-campus surveying, production serving, backup restore and whole-system release validation remain later gates. Node color-environment and expected reduced-motion warnings appeared in browser logs without test failures. This is a fictional development demonstration, not verified campus guidance.
