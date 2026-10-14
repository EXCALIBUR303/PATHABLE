# PathAble final engineering audit — Phase 8

Audited 2026-10-13–14 (Asia/Kolkata). Authorized by the user's “continue” after the Phase 7 handoff and resumed on 2026-10-14. Scheduled model/effort: GPT-6 Astra / Extra High; actual runtime identity/effort cannot be independently verified. Existing files remain locally saved and uncommitted on unborn `work`. No commit, push, public deployment or environment publication is included.

**Phase 8 is complete for the controlled synthetic demonstration and locally verified release candidate.** All 20 final success criteria are mapped to implementation and executed evidence or explicit limits below. Six findings were repaired and verified. Public navigation readiness is not established.

## Scope and architecture

This audit inspected actual API handlers, services, schemas, SQL migrations/triggers/grants, pure graph algorithms, client request/session/event/route state, admin review and analytics screens, ML data/training/worker boundaries, release containers, CI and backup scripts. Previous phase summaries were context; implementation inspection, reproduced failures and new executions supply the conclusions below. This is an independent review pass in the same workspace, not an external penetration test or accessibility certification.

The application is a modular FastAPI monolith with PostgreSQL 17/PostGIS 3.5, SQLAlchemy and three Alembic migrations. React/TypeScript uses TanStack Query, Leaflet, Radix-based controls and charts with text tables. The UI renders backend route geometry. Opaque HttpOnly cookie sessions, CSRF with exact Origin, Argon2id and server ownership/role checks protect private operations. Native development uses Vite's same-origin API proxy; the release candidate serves compiled static assets and API/SSE through HTTPS Nginx. No paid map API, external tiles, route history, result cache or distributed broker is required.

Graph-changing services lock a campus revision, apply CAS, and commit graph changes, audit and durable events together. Report verification creates source-specific physical-edge restrictions. Resolving one report releases only its own restrictions. Pending reports and accepted model annotations cannot alter route eligibility. The optional worker has a separate restricted DB role, bounded CPU subprocess and leased durable jobs.

## Routing assessment

The routing module imports no HTTP or ORM code. It validates graph structure, finite positive lengths, matching geometry endpoints and the WGS84 ECEF chord lower bound before using A*. Hard constraints remove inadmissible arcs; unknown or expired measurements cannot prove stairs, grade, width or surface requirements, even under permissive uncertainty settings. Physical closures and mapped unavailable infrastructure affect both directions. Nullable observations remain nullable.

Dijkstra and A* use the same nonnegative `walking-effort-v1` cost. A* uses a chord-distance heuristic whose admissibility/consistency follow from the checked edge lower bound and triangle inequality. Independent exhaustive tests enumerate physical graph records without calling the implementation's filtering or cost helpers. Directed/parallel edges, equal costs, tiny improvements, reverse geometry, same-node Point routes, disconnected graphs and invalid data are exercised.

Bounded Yen search requests at most two additional loopless routes, filters costs above 1.5 times the optimum and requires at most 80% shared physical length. Rejected diversity candidates still participate in enumeration. A shared 100,000-expansion/two-second budget and 20 popped-candidate cap prevent unlimited searches. Primary exhaustion returns a service error; secondary exhaustion retains the proven primary with explicitly incomplete alternatives. This is bounded practical alternative generation, not a guarantee that every qualifying alternative is returned.

The adapter loads one read-only repeatable-read snapshot and validates revision, policy, cost version and expiry after calculation, with one bounded retry. The client cancels superseded requests, retires known-stale guidance, monitors SSE/heartbeat/reconnect/offline/expiry and polls versions. Automatic rerouting preserves the trip/profile and requires explicit confirmation before guidance resumes.

## Findings and repairs

| ID | Impact and reproduction | Repair and verification |
| --- | --- | --- |
| A8-01 | Medium: a base64 JSON cursor with numeric `id` reached `UUID()` and produced 500 instead of a client error. The public read-only reproduction returned `INTERNAL_ERROR`. | Validate cursor object/string field types before parsing. Five malformed-field regressions require 400; existing pagination behavior remains covered. |
| A8-02 | Medium: unexpected exceptions handled by Starlette outside user middleware lost no-store/nosniff/request-ID headers. A8-01 reproduced the missing headers. | The problem-response helper emits privacy/correlation headers itself; normal middleware sets them without duplicates. A real authenticated edit with an injected post-write exception proves 500 redaction, headers and DB rollback. |
| A8-03 | High recovery impact: checksum validation accepted a manifest without `migration_revision`, although restore accessed it after importing data. A synthetic non-dump probe demonstrated acceptance without executing a restore. | Validate the full manifest's shape, revision, aware timestamp, source project and typed size/hash entries before contacting the target. Nine malformed-metadata cases prove no target operation occurs. Existing corruption/membership/traversal/symlink checks remain. |
| A8-04 | High recovery impact: mode-0600 staged files inherited the operator UID. Root-operated recovery for a non-root API would leave private evidence unreadable. | Staging assigns the configured runtime UID/GID before import. A mismatched unprivileged operator is rejected before DB mutation. A network-isolated container ran the actual copy helper as root and then read exact private bytes as UID/GID 12345; modes remained 0700/0600. |
| A8-05 | High configuration impact: owner/application/worker names could coincide. A settings-only probe accepted application=owner; such a binding can collapse privilege separation or cause worker grant resets to revoke app access. No colliding roles were created. | Settings and operator configuration reject collisions before DB operations. All three role-pair collisions and the operator-file boundary have regressions. Existing distinct-role configuration remains supported. |
| A8-06 | Medium startup reliability: the first Vite launch recorded a transient pre-exec `[node]` command. A later startup refused that same child because its final command differed. Exact start time, expected argv and working directory confirmed the process belonged to this audit. | API/frontend helpers record ownership only after the expected command appears. Four deterministic regressions cover transient identity and refusal to signal mismatched processes. Real startup and repeat startup pass; a subsequent runtime had no live process at the stale PID and safely replaced the dead record without signaling another process. |

No unresolved critical routing, authorization or transactional integrity defect was identified in the inspected scope. That statement does not establish absence of defects beyond the exercised controls. Public operational gaps below remain release blockers. No broad redesign or migration was needed for these repairs.

## Final success criteria: implementation and evidence

“Verified locally” refers to synthetic controlled fixtures and executed checks, not surveyed campus suitability. Test file references identify assertions exercised by the application suites.

| Brief criterion | Implementation inspected | Evidence / qualification |
| --- | --- | --- |
| 1. Authentication | [auth service](../backend/app/services/auth.py), session/login/logout APIs, client session generation guards | Auth integration and real browser security/account scenarios: rotation, expiry/revocation, cookie flags, CSRF, ownership and logout. |
| 2. Real persistence | [migrations](../backend/alembic/versions/0001_foundation.py), PostGIS geometry/constraints and restricted roles | Fresh test DBs use actual PostGIS; retained restart and coordinated release restore exercise durable records. |
| 3. Interactive frontend | [pages](../frontend/src/pages/Navigation.tsx), real API mutations, shared UI primitives | Component/type/lint/build and real desktop/mobile account/admin flows; no fabricated successful submissions. |
| 4. Campus mapping | [CampusMap](../frontend/src/features/navigation/CampusMap.tsx), GeoJSON API, text pathway list | Live synthetic geometry, location/entrance selection and built-browser SVG. No surveyed Woxsen map. |
| 5. Dijkstra | [engine](../backend/app/routing/engine.py) | Exhaustive/generated oracle, API comparisons and browser algorithm selection. |
| 6. A* | Same pure engine, checked ECEF heuristic | Independent oracle and all-simple-path heuristic checks; no degree-as-metre heuristic. |
| 7. Accessibility constraints | Eligibility filtering and nullable schemas | Critical A/C/G: stairs, exact grade/width boundaries, unknown/stale facts, mapped dependencies and no-route. |
| 8. Alternatives | Bounded Yen search and physical-length diversity | Oracle/cutoff/budget/API/browser assertions; incomplete search is explicitly reported. |
| 9. Accurate visualization | Server geometry/totals/instructions, initial SVG options | Critical I: selected/alternative geometry and totals; production browser check catches the earlier Strict Mode-masked class problem. |
| 10. Obstacle reports | [reporting](../backend/app/services/reporting.py), private bounded evidence | Submission/history/ownership/idempotency, real normalized image tests and browser upload/error states. |
| 11. Admin verification | Fresh actor locks, CAS, source restrictions, audit | Critical E/K: permission revocation, concurrent/replayed decisions, rollback and immutable history. |
| 12. Dynamic infrastructure | [graph service](../backend/app/services/graph.py), SQL integrity, version/event bump | Real geometry/admin edits, incident-edge updates, expiry and event assertions. |
| 13. Recalculation | [route hook](../frontend/src/features/navigation/useRouteCalculation.ts), durable replay/reset | Critical B/L: real report-to-retirement-to-confirmed-reroute, no-route after closure, reconnect and stale response cancellation. |
| 14. DB analytics | [SQL aggregates](../backend/app/services/analytics.py), chart/table UI | Physical-edge/report grain, no evidence/restriction fan-out, inclusive/exclusive flow dates and null empty means/coverage. |
| 15. Honest AI integration | Dataset audit, CPU pipeline, safe assets, restricted worker and annotation review | Critical F and ten actual CPU pipeline tests use labeled fixtures. No approved data/evaluated product weights; `ML_ENABLED=false`. No hazard metrics or live product inference claim. |
| 16. Secure API | Auth/ownership/Origin/CSRF, bounded input/uploads, redacted problems, DB grants | Negative API/browser tests, fresh role checks, private-file checks and release HTTPS/headers. Public proxy admission still unresolved. |
| 17. Reliable errors | Problem responses, rollback, no-route distinction and UI recovery | DB outage, malformed input, decoder timeout, stale CAS, route budget and new unexpected-error rollback regression. |
| 18. Automated tests | [test wrappers](TESTING.md), real disposable databases, independent routing oracle | Exact current counts/results below. Zero-test, skipped or unavailable functionality is never counted as working. |
| 19. Reproducible environment | Hash/npm locks, pinned images, install/start scripts and saved cloud instructions | Current startup and clean local source-export release build. Remote Git/hosted CI/macOS/new cloud restoration remain unverified. |
| 20. Documentation | Contracts/ADRs/runbook/demo/status plus this report | Current claims reconciled with code and results; local Markdown links/JSON/whitespace checked before handoff. |

The 20 Phase 8 audit areas are covered by this mapping plus the sections on architecture, algorithms, failures, security, performance, accessibility, maintainability and unfinished operations. Critical A–L remain the acceptance scenarios in [TESTING.md](TESTING.md); F verifies isolation/unavailability, not trained model quality.

## Verification record

All commands run from `/workspace/PATHABLE` unless a working directory is stated. The workspace is uncommitted, so no commit SHA is fabricated. Logs were captured under `/tmp/pathable-p8-*.log`; October 13 temporary logs did not survive the resumed runtime, so their observed counts are preserved here. October 14 startup/helper/release logs are current execution artifacts. Nonprivate durable metadata is retained in `docs/examples/`.

| Command | Current audit result |
| --- | --- |
| `bash scripts/start.sh` | Passed actual DB/API/UI readiness, public graph/routes, direct/proxied SSE and explicit ML DISABLED; real owned API/frontend stop/start and repeat startup passed again on October 14 after the identity fix. |
| `bash scripts/test.sh` before repairs | 332 passed, 48.15s. |
| `cd backend && ../.venv/bin/pytest app/tests/integration/test_security_review.py -q` | 13 passed, 3.04s after cursor/header repairs. |
| `bash scripts/test.sh` after final repairs | Ruff/format passed; **341 passed**, 54.97s, zero failures/skips/xfails. |
| `bash scripts/test_frontend.sh` | Contract/type/lint/format/build passed; 41 component tests in 10 files (3.97s); 22 browser tests (1.7m), one worker, no retries/skips/failures. |
| `bash scripts/test_ml.sh` | 10 passed, 2.69s; synthetic CPU execution only. |
| `.venv/bin/pytest scripts/tests/test_backup_manifest.py -q` | 18 passed, 0.05s, including manifest, identity and role-configuration regressions. |
| `.venv/bin/pytest scripts/tests -q` | **22 passed**, 0.06s on October 14: the 18 recovery/configuration tests plus four process-ownership regressions. |
| `.venv/bin/python /tmp/pathable-p8-owner-probe.py` | Passed real root-to-UID12345 private staging/reading in a disposable network-isolated container; no application data touched. |
| `bash scripts/test_release.sh` | **Exit 0 on October 14**: helper lint/format, 22 operator-helper tests, verified artifacts/offline images, strict HTTPS and compiled-browser auth/routes, actual coordinated private-image restoration, retained restart, occupied-target refusal and no-cache clean source-export build with fresh migration/seed/HTTPS. |
| `.venv/bin/python scripts/verify_persistence.py` | Passed October 13 and repeated October 14: user/session/profile/saved destination/graph survived owned API and DB restart with the volume retained. Temporary account cleaned up. |
| `.venv/bin/python scripts/benchmark_routing.py` | 20 synthetic pure-engine calculations completed with matching optimal primary costs; result detail below. |

The backend emits one existing Starlette/httpx deprecation warning. Browser runs emit color-variable/reduced-motion notices. These are not skips or assertion failures. Initial repair lint found an unused loop variable (fixed) and a Ruff source-root mismatch when invoked from the repository root (rerun from documented `backend/`); no rule was disabled. The two startup-race tests first failed because the filesystem sandbox denied their local socket probes, before reaching the ownership assertions. The elevated rerun was initially not executed because automatic approval review hit the usage limit (not a safety rejection); on October 14 it executed and all 22 helper tests passed. The existing CI workflow was inspected and its wrappers executed locally; actionlint passed in Phase 7, but that temporary binary is absent in this instance and it was not rerun. Hosted GitHub CI remains unrun.

Release execution metadata is retained in [the Phase 8 result artifact](examples/phase8-release-validation.json). It describes actual copied private-image bytes and database objects; the model-storage probe is an explicitly inert text file, not registered weights. Test/restore/clean-source fixture services were stopped afterward, preserving their private files and DB volumes. The clean build exports local nonignored files from this unborn checkout; it is not a remote Git checkout or hosted CI run. Current OpenAPI still has 47 operations on 43 paths. Generated-contract verification passed, and private configuration/uploads/models/environments remain ignored by Git.

The final October 14 development-database check found no registered models, inference jobs, predictions, active SSE leases, disposable test databases/ML roles or persistence-test accounts. Real frontend stop/start, API/database retained-volume restart and repeated startup all passed. Final documentation checks cover 281 nonignored files, JSON parsing, local Markdown links and whitespace, plus `git diff --check`.

Reusable cloud startup instructions were saved and read back exactly at draft revision 12. The install script, repository selection, network policy and credential/runtime requirement metadata were preserved. The draft still requires publication; review/save the environment settings, then publish when ready. Saving the draft does not prove fresh-task or volume restoration and did not publish the environment.

## Performance, accessibility and maintainability

[Current benchmark metadata](examples/phase8-benchmark.json) records Python/platform, all 20 runs and five cases per algorithm/alternative group on a 2,000-node/5,000-physical-edge synthetic graph. Nearest-rank P95 primary times were 106.9ms Dijkstra and 89.7ms A*. With up to two alternatives requested they were 460.3ms and 501.3ms. All ten alternative requests hit the expansion bound and correctly reported incomplete alternatives; optimal primary costs agreed. These are small-sample pure-engine measurements, excluding HTTP/DB and taken during a backend audit run. They are not concurrent service capacity or an SLA. The older Phase 6 Dijkstra-alternative P95 of 1.66s exceeded the planning target; this faster run does not erase that observation.

The current real report/browser pipeline retired its obsolete overlay in **956ms** after verification began, below the two-second test threshold for this one connected synthetic scenario. Stream loss/offline and replay tests also pass; capacity at 200 admitted streams and production client-IP attribution are unmeasured.

Browser axe checks exercise WCAG 2/2.1 A/AA rules without exclusions across public/account/admin/populated review views. Public 320-CSS-pixel reflow, keyboard focus restoration, reduced motion, text map alternatives and analytics tables are covered. These automated checks do not replace screen-reader, motor/cognitive usability or real assistive-technology evaluation.

Current generated screenshots were also visually inspected: the production route shows the selected SVG, 44.4m backend total, an alternative, matching text directions and synthetic/currentness caveats; the admin screen shows consistent controls, report state, database metrics, chart tables and audit history. This is visual review of synthetic fixtures, not user research.

The pure algorithm boundary, explicit transaction services, frozen contracts, hash locks and scenario tests support maintenance. Complexity is concentrated in route/event state, report/evidence transaction coordination and operator recovery. Preserve their existing concurrency tests when changing them. SQL is explicit and migrations are independently exercised; release/test scripts are sequential where they restart shared services. Future work should improve measured bottlenecks and operator observability without splitting the monolith speculatively.

## AI status and unfinished functionality

The code implements licensed manifest review, group/hash/perceptual split-leakage checks, deterministic small-CNN CPU training, held-out classification evaluation, safetensors-only assets, checksums/provenance, private leased inference and human annotation review. Registration rejects synthetic fixtures for product use. Predictions are uncalibrated class scores, not route-safety probabilities, and acceptance cannot create infrastructure restrictions.

Approved hazard imagery/rights/annotations and evaluated product weights are missing. No real training quality, hazard accuracy, calibration or generalization result exists. ML stays disabled. Licensed data acquisition, independent holdout evaluation and operator review are prerequisites before enabling the optional worker. It must also be added to backup quiescence and production monitoring before operation.

## Deployment conclusion and next priorities

The intended outcome is a controlled local synthetic technical demonstration and prepared release candidate. Public navigation deployment is **not approved or established** by these tests. Remaining gates are:

1. Obtain authorized surveyed campus data, verify connectivity/measurements and establish accountable review/freshness practices. Synthetic coordinates are not a real Woxsen navigation map.
2. Design trusted proxy/client-IP admission and test representative load. Anonymous buckets and stream identities currently aggregate behind Nginx; proxy identity is deliberately not trusted from arbitrary headers.
3. Validate public DNS/certificate issuance/renewal, host/container OS security, monitoring/alerts, encrypted off-host retention/recovery and privacy/account-export/deletion policy. Phase 6 package advisory scans were clean at that snapshot; they are not an OS audit or a fresh external security assessment.
4. Run manual assistive-technology/user evaluation and address findings before navigation reliance. No legal accessibility or individual-suitability claim is made.
5. Run hosted CI and platform-specific setup (especially Apple Silicon amd64 emulation). Preserve the unborn/local source in the environment snapshot; no remote clone or fresh-task restoration has been independently verified. The bundled Chromium CDN was blocked in Phase 7; current browser tests use system Chromium.

Backups remain trusted-operator input: checksums detect corruption, not authenticity. Serialize operator/release builds on their shared builder; cache-ID cleanup assumes no concurrent unrelated build. Quiesce external writers during snapshots. Keep services stopped if a post-import filesystem/grant/schema check fails and investigate rather than retrying against a now-populated target. Existing roles' passwords are not automatically rotated by `prepare-db`; coordinate application-role credential rotation explicitly with the database operator.

There is no Phase 9 in the approved schedule. After verified Phase 8 completion, stop for a user-selected follow-up scope. Further audit/remediation can use the scheduled GPT-6 Astra / Extra High; any model/effort changes remain manual. Commit, push, public deployment and environment publication remain separate actions.
