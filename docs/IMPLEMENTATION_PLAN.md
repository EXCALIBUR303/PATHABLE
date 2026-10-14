# Phased implementation plan

The user authorized Phase 8 by sending “continue” after the Phase 7 handoff. Phases 1–5 are implemented with ML explicitly resource-limited; Phases 6–7 scoped integration and local release preparation are verified. Phase 8 audits actual source/results and fixes scoped defects; see [final audit](FINAL_ENGINEERING_AUDIT.md). Authorization ends at Phase 8. Completion requires file inspection, actual phase-appropriate validation, status/evidence updates and an explicit stop. An unresolved required check prevents that phase from being called complete. Do not commit, push, deploy or publish without separate authorization.

## Phase 0 — Architecture and critical engineering design

Requested model/effort: GPT-6 Astra / Extra High.

Deliver architecture/ADRs, schema, routing proof obligations, API contracts, security, reporting/event semantics, frontend/ML plans, risk register, assumptions, acceptance criteria, phase/model continuity, scaffold and design validation. No backend application, migrations, frontend implementation, production algorithm or ML training.

Acceptance: every required document exists; no unresolved architecture contradiction blocks Phase 1; links and scaffold validate; independent small design-fixture enumeration checks cost/constraints/alternatives and heuristic inequalities; color token checks validate proposed pairs. Record these as design checks, not application tests. Stop after the final Phase 0 report.

## Phase 1 — Backend, database, authentication and APIs

Model/effort: GPT-6.1 Sol / High.

1. Inspect status/contracts and worktree; configure FastAPI settings, Python environment, hashes/locks, pytest/ruff. Confirm selected dependency compatibility rather than blindly following registry latest.
2. Add Docker Compose PostgreSQL/PostGIS with health check, named persistent volume, explicit image version/digest, local-only DB port, secure local credentials and Mac compatibility check. No paid service.
3. Implement initial models/migrations for users/sessions/profiles/saved destinations/campus graph/infrastructure/graph_state/audit/events. Reserve reporting/ML contract shapes; their full tables and behavior arrive in P4/P5 migrations, not fake handlers.
4. Implement authentication, CSRF, role/ownership checks, rate limits, profile/location/infrastructure/saved APIs and structured errors. Provide an explicit secure admin-creation command.
5. Implement reusable graph mutation/version/freshness primitives now, including CAS, audit and durable event insertion. API node/edge/infrastructure management uses these; SSE distribution remains P4.
6. Seed deterministic fictional infrastructure with two admissible alternatives, stairs shortcut, unknown/narrow/steep/gravel/blocked paths and meaningful access points. Seed must not overwrite later edits. It must use real geographic geometries and PostGIS-derived lengths; do not copy the toy design fixture distances into a DB as measured data.
7. Execute migrations on clean DB and upgrade path, seed twice, start API, perform real auth/profile/infrastructure requests, validate rollback/concurrency and restart persistence.

Acceptance: actual API starts; readiness verifies PostGIS/migration version; authentication/session revocation/CSRF/ownership work; constraints and migrations pass real DB tests; seed is repeatable without duplication; data survives API/database container restart without deleting volumes (critical H); ordinary user fails privileged operation tests (E foundation); no source dummy route/report successes. Save tested cloud installation/startup instructions only once these operations work. Stop; next P2 uses the same model/effort.

## Phase 2 — Frontend, brand and maps

Model/effort: GPT-6.1 Sol / High.

Implement Vite/React/TypeScript, locked dependencies, tokens/logo assets, accessible primitives, layout/pages, auth/profile/saved flows, location search and real graph/infrastructure rendering via generated API types. Route/report/admin controls whose backends are not yet implemented show honest unavailable states. Implement map/text parity, loading/error/empty/success states, reduced motion and keyboard form flows. Add Vitest/Testing Library and live-API Playwright checks.

Acceptance: typecheck/lint/unit tests and production build pass; actual registration/login/profile persistence and map data work against P1; essential desktop/mobile navigation and keyboard paths operate; unavailable controls do not fabricate production behavior. Inspect UI in a real browser. Stop; next P3 requires model/effort switch.

## Phase 3 — Routing and graph algorithms

Model/effort: GPT-6 Astra / Max.

Implement snapshot construction/validation, hard filtering, versioned cost, pure Dijkstra/A*, admissible ECEF heuristic, Yen alternatives with bounds, no-route/same-node handling, geometry/instructions, route API and real frontend route rendering. Exercise graph mutation primitives through admin infrastructure APIs before P4 reporting exists. Benchmark the representative campus without compromising constraints; instrument expansions/time.

Acceptance: critical A/C/D/G/I pass; compare algorithms to independent exhaustive oracle plus generated graphs; alternatives satisfy eligibility/diversity and primary remains optimal; both directions of closed physical paths disappear; no unknown data appears verified safe; graph edits invalidate previous routes (B foundation/L no-cache version checks). Budget exhaustion is not misreported as no-route. Stop; next P4 switch.

## Phase 4 — Reporting, admin analytics and live updates

Model/effort: GPT-6.1 Sol / High.

Add report/evidence/restriction/idempotency migrations and services; private bounded uploads; review/history/audit; source-specific resolution; durable SSE replay/expiry and frontend rerouting; DB-backed analytics with explicit definitions and accessible Recharts/table views. Extend existing graph mutation service rather than introducing a parallel version source.

Acceptance: real report submission/evidence/review changes actual route eligibility; critical B/E/J/K/L pass through real DB/API and browser; verify multiple hazards, idempotent replays, optimistic conflict, crash rollback and replay after reconnect; analytics calculations have denominator/grain tests. No stale route is shown as current after a known event. Stop; next P5 switch.

## Phase 5 — AI/ML integration

Model/effort: GPT-6 Astra / Extra High.

Audit datasets/licenses/annotations/resources first; select classification vs detection based on actual annotations. Build loaders, preprocessing, training/evaluation scripts, asset manifests, optional leased jobs, versioned inference and prediction review UI. Evaluate real weights with a held-out split and record limitations/metrics only when actually measured. Keep core app independent.

Acceptance: critical F plus missing/failed inference behavior pass. Fully available inference requires verified weights, reproducible held-out evaluation, real stored predictions and correct review integration. If data/weights/compute are unavailable, complete executable training/interface/failure-handling work, list precise external blockers, mark ML limited/blocked and stop; never claim trained functionality. Next P6 requires authorization even with the same model.

## Phase 6 — Integration, security and defect fixing

Model/effort: GPT-6 Astra / High.

Execute backend, graph, frontend and real end-to-end flows; reproduce/fix cross-module defects; review sessions, CSRF, permissions, private uploads, DB consistency, events/freshness, dependency/network failures, privacy and accessibility. Benchmark observed bottlenecks; avoid broad UI rewrites without demonstrated defects.

Acceptance: all applicable critical A–L tests execute and pass; blocked ML capability stays honestly disabled; no unresolved critical security/data-integrity defect; reports reflect actual test results including skips/failures. If a required check cannot run, report the blocker instead of declaring completion. Stop; next P7 switch.

## Phase 7 — Deployment preparation and documentation

Model/effort: GPT-6.1 Sol / Medium.

Finalize containers/Compose, health/migration/seed/start/build commands, CI jobs, environment templates, Mac instructions, backups/restore, demo script and professional README. Validate on clean checkout and clean DB plus retained-data restart; make reviewed cloud setup/start instructions reproducible. Prepare release configuration, never push/deploy without explicit authorization.

Acceptance: documented commands execute successfully, CI config matches actual scripts, production build/start and smoke flows work, backup restore is verified and honest ML/real-campus limitations remain visible. Publishing cloud environment is separate user action; saved draft is not a deployment. Stop; next P8 switch.

## Phase 8 — Independent final engineering audit

Model/effort: GPT-6 Astra / Extra High.

Inspect actual code and results, not prior completion claims. Audit architecture, UI, API, DB, routing, constraints, events, admin permissions, AI, validation, security, test coverage, builds, deployment, performance, accessibility and unfinished features. Run pertinent checks, fix critical feasible defects, document unresolved issues and issue a technical report with evidence.

Acceptance: every final success criterion maps to implemented code and executed evidence or a clearly stated limitation; no production-readiness claim without supporting security/reliability/operations evidence. Stop for user's next direction.

## Traceability to the project success criteria

| Success requirement | Owning phase / evidence |
| --- | --- |
| Authentication, real PostgreSQL persistence, secure access | P1/P6: API/security integration + H/E |
| Professional interactive UI and real campus geometry | P2/P6: browser/keyboard checks, real API data |
| Dijkstra, A*, restrictions, alternatives, visualization | P3: A/C/D/G/I, oracle and generated-graph tests |
| Reporting, verification, recalculation, analytics | P4: B/E/J/K/L, DB aggregate evidence |
| Honest AI capability/status | P5: real evaluation if available, F and unavailable-mode tests |
| Reliability, automated tests and error handling | P1–P6: DB/network/graph/upload failure tests |
| Reproducible setup and professional documentation | P7: clean install/build/restart/restore evidence |
| Whole-system demonstration and limitations | P8: independent audit and complete report-to-reroute demo |
