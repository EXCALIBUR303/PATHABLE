# ADR-011 — Phase 2 frontend and browser validation

Accepted 2026-10-12; supplements the Phase 0 frontend plan.

**Problem:** A real frontend needs compatible dependencies, cookie/CSRF session continuity, honest capability boundaries, accessible map alternatives, and browser tests that preserve developer data.

**Decision:** Use Vite 8.3.4, React 19.3.0, TypeScript 5.9.3, Tailwind 4.3.3 and the resolved npm lock on Node 24. Phase 0's TypeScript 7.0.2 was a candidate; openapi-typescript 7's supported peer range requires TypeScript 5.x. Select stable 5.9.3 without forcing peers. ESLint 10 and typescript-eslint resolve with supported peers. Generate types from the actual Phase 1 OpenAPI; fail checks on drift.

Use same-origin fetch through Vite's API proxy, HttpOnly cookie sessions, and session-bound CSRF held only in memory. Bootstrap requests share one flight and a generation/abort guard; login/logout cannot be overwritten by a stale bootstrap response. Keep the active session-query observer when clearing prior private data. Mutation failures are not automatically retried. Profile editing retains the draft's original row version across background refetch; conflicts require explicit reload/reconsideration.

Render real backend graph GeoJSON and infrastructure, with selected entrances represented by path-node IDs. Geometry works without tiles. Fictional landscape decorations are illustrative; they are not surveyed building footprints or route results. Searchable locations and text pathways convey the same observations and unknown measurements. Source components use Radix/Slot/CVA, with semantic CSS/Tailwind tokens, self-hosted licensed Inter, custom SVG brand assets and reduced motion. No generated shadcn registry code is required. Route/report/analytics/ML capability flags remain false; the report form is a local, unsaved draft and the admin observation chart counts actual infrastructure records.

Browser tests provision a fresh UUID-named PostGIS database, migrate/seed it and add an administrator only within that test database. Playwright uses separate API/UI ports 18000/5174, one worker, no retry and no reuse of unknown existing listeners; graceful teardown removes only its generated database. Vite uses distinct optimizer cache directories for development and E2E. The available system Chromium is used; bundled browser installation is a documented alternative, unexecuted here.

**Alternatives:** Browser storage for bearer tokens increases exposure and complicates revocation. Removing an active session query can strand subscribers. Remounting versioned forms on each refetch loses unsaved edits. Running browser tests against the developer database risks destructive fixture resets. Hosted tiles add an unnecessary key/network/license prerequisite for the synthetic campus.

**Validation:** Generated-contract check, strict TypeScript, ESLint, Prettier, 15 component/API tests, 7 real full-stack browser tests, production build, screenshot inspection, repeated frozen install/start and owned frontend stop/restart. Exact results and limitations are recorded in [Phase 2 evidence](../PHASE2_TEST_EVIDENCE.md).
