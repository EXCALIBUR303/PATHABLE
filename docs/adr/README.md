# Architecture decision records

Accepted for Phase 0 implementation planning. A future change needs evidence, a migration/compatibility plan, and a superseding ADR; do not silently rewrite the baseline.

| Record | Decision | Alternatives and tradeoffs | Validation gate |
| --- | --- | --- | --- |
| ADR-001 | Modular monolith, PostgreSQL/PostGIS, pure routing module | Microservices add deployment/consistency overhead; SQLite cannot validate PostGIS or real transactional locking. A monolith has fewer operational boundaries but must enforce module imports. | Phase 1 real DB integration; Phase 3 routing imports no web/ORM modules |
| ADR-002 | Opaque server sessions in HttpOnly cookies, CSRF protection | JWT bearer tokens make stateless distribution easy but complicate revocation and browser storage; database sessions add lookup cost and simplify role/session invalidation. | Login/rotation/logout, CSRF, stale-role and ownership tests |
| ADR-003 | Physical pathways expand to directional arcs; hard filtering then cost optimization | Independent unrelated reverse edges make closures inconsistent; large penalties can still route across prohibited features. Physical IDs preserve reporting semantics. | Constraints A/C/G and bidirectional closure fixtures |
| ADR-004 | Metre-equivalent cost and ECEF chord A* heuristic | Raw degree distance is invalid; spherical distance may overestimate spheroidal length; h=0 is correct but offers no search guidance. ECEF chord is conservative and requires no geodesic library in the engine. | Algebraic consistency review plus generated Dijkstra/A* equivalence tests |
| ADR-005 | Graph version, restriction ledger, audit, durable event in one transaction | In-memory broadcasts can lose updates; report resolution setting `open` directly can erase other closures. Durable events and a restriction ledger add tables but preserve consistency. | Concurrent review, two-obstacle resolution, crash/replay and stale-cache tests |
| ADR-006 | No initial route-result cache; later cache keyed by complete revision/profile/model | Unversioned cache creates stale routes; Redis is unnecessary at campus scale. Per-request snapshot construction costs DB work; optimize only after measuring. | DB outage and stale revision tests; enforce contract if caching introduced |
| ADR-007 | Optional human-reviewed ML worker, model choice deferred to dataset audit | Mandatory inference would make reporting depend on weights/compute. Generic image labels cannot establish specialized hazard detection. Honest disabled state retains a functioning product. | License/annotation audit, held-out evaluation, no-AI-route-mutation test |
| ADR-008 | React/Leaflet with no mandatory external basemap | Hosted geospatial platforms add key/license/network dependencies; self-hosted tile infrastructure is excessive for a synthetic campus. Geometry-only mapping works offline but lacks general-world cartography. | Tile-disabled visual and keyboard/text navigation checks |
| ADR-009 | Freshness deadlines are graph validity boundaries | A permanent `verified` flag ignores aging; a time-only eligibility rule without version changes invalidates cache assumptions. The shared expiry transaction adds scheduling work but preserves revision semantics. | Clock-controlled expiry event, request-boundary refresh, and replay tests |

Owners: architecture baseline — Phase 0; implementation evidence — owning phase in [implementation plan](../IMPLEMENTATION_PLAN.md). These decisions do not prove operational readiness.

[ADR-010: Phase 1 runtime and validation](010-phase1-runtime.md) records the verified image architecture, frozen migrations, DB privileges, transaction/read behavior and validation strategy.

[ADR-011: Phase 2 frontend and browser validation](011-phase2-frontend.md) records compatible dependency selection, session/draft concurrency, geometry rendering and disposable browser-test databases.

[ADR-012: Phase 3 routing and snapshot validation](012-phase3-routing.md) records pure constrained searches, bounded alternatives, RFC 8785 profiles, repeatable-read snapshots, resource/pool bounds and route currentness.

[ADR-013: Phase 4 reporting and live updates](013-phase4-reporting.md) records reviewed restrictions, private normalized evidence, durable replay/leases, fetch-stream heartbeat monitoring, optimistic drafts and aggregate grain; accepted 2026-10-13 with [Phase 4 evidence](../PHASE4_TEST_EVIDENCE.md).

[ADR-014: Phase 5 optional CPU ML](014-phase5-optional-ml.md) records the resource-limited classifier pipeline, immutable evaluated assets, restricted worker leases and annotation-only review. See [Phase 5 evidence](../PHASE5_TEST_EVIDENCE.md); trained hazard capability remains unavailable.

- [ADR-015: HTTPS release operations and coordinated backups](015-phase7-release.md).
