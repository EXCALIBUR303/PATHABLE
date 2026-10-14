# Phase 2 executed evidence

Executed 2026-10-12 in `/workspace/PATHABLE`, after user authorization for Phase 2. Scheduled setting: GPT-6.1 Sol / High; runtime model/effort identity is unverified. Scope ends here, before Phase 3 routing.

## Environment and dependency checks

Node 24.19.0, npm 11.9.0, Python 3.12.14, Docker/Compose and the existing digest-pinned PostgreSQL 17.5/PostGIS 3.5 support the live workflow. Browser: system Chromium 154.0.8037.57 on Debian 13, driven by the locked Playwright 1.64.0. Vite 8.3.4, React 19.3.0, TypeScript 5.9.3, Tailwind 4.3.3, Vitest 5.0.4, Leaflet 1.9.4 and React Leaflet 5 resolve/install without peer overrides. TypeScript differs from the Phase 0 candidate for the supported openapi-typescript peer range; see [ADR-011](adr/011-phase2-frontend.md). Inter's license is retained in the frontend public assets.

Actual `bash scripts/install.sh` repeat run completed with hashed Python installation, healthy retained DB, migrations/grants, preserve-existing seed and `npm ci` (378 packages). Root `.env` and developer data were preserved. Workspace caches avoid writes into the read-only home. No TLS/hash/signature verification was disabled.

## Final frontend validation

From repository root:

```sh
bash scripts/test_frontend.sh
```

Final wrapper exit status: **0**. It executed, in order:

| Command, from frontend/ | Actual final result |
| --- | --- |
| `npm run api:check` | Generated TypeScript matches actual backend OpenAPI; passed |
| `npm run typecheck` | Strict TypeScript; passed |
| `npm run lint` | ESLint; passed |
| `npm run format:check` | All matched files use Prettier style; passed |
| `npm test` | **15 passed, 5 files, 5.27s**; no failed/skipped tests |
| `npm run build` | Typecheck and Vite production build passed; Vite build 1.04s |
| `npm run test:e2e` | **7 passed, 55.2s**, one worker, zero retries; no failed/skipped tests |

Component/API tests isolate HTTP with test fixtures only; production adapters call real APIs. They cover serialization/cookie/CSRF, preserved password whitespace, cancellation and session races, conflict handling/no mutation retries, network/pagination, keyboard search/empty/Escape, nullable constraints and numeric bounds, unsaved profile drafts during background changes, optimistic conflicts, protected roles and network errors.

Production JavaScript is split across pages/map/chart modules. Entry chunk 348.32kB (110.64kB gzip); map 157.99kB (46.59kB gzip); lazy admin/chart 365.03kB (105.72kB gzip). No chunk-size warning. Build success is not a production-serving, deployment or performance-budget certification.

The final log is ignored `/tmp/pathable-phase2-final-check.log`. After the frontend README changed, `npm exec prettier -- --write README.md` and `npm run format:check` passed again. Generated API source and lock are deliberately excluded from manual formatting.

## Real full-stack browser coverage

Playwright starts a new UUID-named PostGIS database, migrates/seeds real tables, creates only its test administrator, and runs API/UI on 18000/5174. No developer database reset, live API reuse, automatic retries or production mocks. A separate optimizer cache avoids disrupting the development Vite process. Each test completed:

1. Landing renders live geometry; keyboard source/destination search and swapping work; route control is honestly disabled; text paths expose unknown observations; no browser page errors in this flow.
2. Actual registration/login, preference save and reload, saved place/dashboard/map selection, display-name edit and logout protection.
3. Ordinary user sees no admin controls; a real privileged API mutation returns **403** with otherwise valid session/CSRF headers.
4. Fixture admin edits actual infrastructure with a reason/version; graph revision increments; the test restores the fictional observation.
5. Explicit test-only injected 503 shows an honest failure; removing the injection and retrying recovers live map data.
6. Mobile 390×844 navigation/dialog Escape restores opener focus, route change dismisses dialog, map works, no horizontal overflow; reduced-motion setting exercised.
7. Community draft remains usable but never issues a report POST or claims upload/submission/persistence.

Browser teardown completed. Owner-side read-only inspection confirmed **zero `pathable_e2e_*` databases** remain. The test admin is not a development credential or bootstrap account. Development graph remains available and seed-preserving startup passed afterward.

Desktop landing/navigation and mobile navigation screenshots were captured by the actual tests and visually inspected: ignored `.local/screenshots/phase2-landing.png`, `phase2-navigation.png`, `phase2-mobile.png`. They contain guest pages only. These show the custom connected-path brand, semantic colors, real geometry, provenance, endpoint controls and text alternatives. No external basemap was configured.

## Startup and helper validation

Executed from repository root:

```sh
bash scripts/start.sh
bash scripts/start.sh
.venv/bin/python scripts/web.py stop
bash scripts/start.sh
.venv/bin/ruff check scripts/web.py scripts/smoke_frontend.py scripts/e2e_backend.py
.venv/bin/ruff format --check scripts/web.py scripts/smoke_frontend.py scripts/e2e_backend.py
bash -n scripts/install.sh scripts/start.sh scripts/test_frontend.sh
```

Repeated start recognized owned healthy services, preserved synthetic data and passed API smoke (readiness, 13 measured edges, access points, anonymous session) and frontend smoke (HTML, compiled React entry, same-origin proxy, actual graph). Owned frontend stop/restart worked without DB reset or signaling an unrelated listener. Helper Ruff/format and shell syntax passed. Initial helper mode/format issues were corrected by executable permissions and the root formatter before the final respective checks.

A separate Chromium probe against the running development frontend/API verified the landing, actual graph layer and navigation, with no page errors. An initial probe raced the deliberate restart and received connection refused; it was sequenced after readiness. Its first SVG visibility assertion also rejected a horizontal zero-height path despite an attached rendered graph; the corrected probe checks the visible map canvas and nonempty real path layer, matching the passing E2E contract. No application behavior was suppressed to pass this probe.

## Failures investigated and fixed

Initial component tests found a Radix Slot multiple-child shape and cross-realm cancellation handling; both were corrected. Profile mutation assertions account for TanStack's mutation context argument. Additional meaningful tests cover stale session flights and preserved background-edit drafts. Final component runs pass all 15 tests.

Early browser runs exposed auth screen state reused across login/register and an active session observer removed during auth cache cleanup. Keyed auth routes, retained session observers and aborted stale bootstrap flights corrected the application defects. Browser helpers wait for completed login response and server-confirmed authenticated session before deliberately hard-navigating. Targeted auth checks and subsequent full suites passed. Final assertions remain enabled, with no E2E retries.

Non-failing runner warnings remain visible: NO_COLOR/FORCE_COLOR environment precedence and Motion's reduced-motion development notice. Phase 1's test-client deprecation is historical backend evidence, not a new Phase 2 failure.

## Saved setup and boundaries

The cloud onboarding tool confirmed `status=saved`, `requires_publish=true` for complete **install_script** and **start_skill**. The installer invokes the tested root wrapper; startup instructions cover retained files, restarted DB/API/UI, owned shutdown/logs, real readiness checks and isolated tests. Unrelated repository/network/credential settings were preserved. Review/save in environment settings and publish for reuse; neither saving nor current validation proves publication/fresh-task restoration.

Phase 1's separate 35 core real-PostGIS tests, 2 CLI tests and retained-volume persistence check are recorded in [Phase 1 evidence](PHASE1_TEST_EVIDENCE.md), not re-counted or claimed rerun here. Full route correctness/alternatives, reporting/review/SSE/analytics and ML remain their later phases. Full WCAG/axe/screen-reader/zoom-reflow audit, all browsers, external tile failures, macOS, fresh-task snapshot/volume restoration, clean production serving/CI and backup restoration were not executed. No verified real-campus navigation, production deployment or publication is claimed. No Phase 2 blocker remains.
