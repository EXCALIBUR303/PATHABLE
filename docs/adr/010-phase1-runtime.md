# ADR-010 — Phase 1 runtime and validation details

Accepted 2026-10-12; supplements, rather than replaces, the Phase 0 contracts.

**Problem:** The backend needs repeatable migrations, limited DB privileges, real spatial integrity checks, stable API types and reliable process restart in cloud and on a MacBook.

**Decision:** Use a hash-locked Python environment and the inspected PostGIS 17/3.5 amd64 image pinned by OCI digest. Record amd64 emulation explicitly because this image has no arm64 manifest. Use distinct owner/application DB roles. Freeze initial Alembic DDL into versioned SQL rather than importing live model metadata during later migrations; PostgreSQL triggers derive geodesic distance and defer endpoint/level/lower-bound checks until the transaction completes. App code forces those deferred checks before serializing mutation responses. Mutable resources use graph lock then row-version comparison; the lock provides serialization and the expected version detects obsolete clients.

Graph reads perform freshness maintenance and then read under the retained campus graph lock in one transaction, guaranteeing a consistent Phase 1 map export. This serializes reads at campus scale; Phase 3 can introduce the planned repeatable-read snapshot plus final version check when routing needs computation outside the lock. Phase 4 adds idle expiry notifications/SSE. There is no current route cache or routing engine.

Cookie CSRF uses a session-bound HMAC with a separate secret; GET session does not invalidate other tabs. Rate limits commit independently so failed login attempts still consume quota. Password whitespace is preserved; input errors omit submitted values. Response models plus structured problem types generate machine-readable OpenAPI. Test databases have fresh UUID names and real PostGIS, allowing concurrency without mutating development data.

**Alternatives:** Dynamic `metadata.create_all` in migrations is shorter but changes historical migrations when models evolve. Owner credentials for the API simplify grants but expose DDL/audit mutation. A multiarch image could avoid emulation, but an unverified replacement would lose reproducibility. In-memory rate limits would reset/bypass across processes. Explicit frozen migrations/roles and real DB tests provide stronger guarantees with modest setup cost.

**Validation:** Fresh test DB migrations, repeated head upgrade/install/seed, real auth/CSRF/role/ownership tests, graph geometry rollback/CAS/concurrency tests, append-only/schema privilege checks, generated OpenAPI and live API/DB retained-volume restart. Results are recorded in [Phase 1 evidence](../PHASE1_TEST_EVIDENCE.md). Mac execution and new cloud-task snapshot restoration remain unverified.
