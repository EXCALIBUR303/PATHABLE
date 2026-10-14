# Phase 4 — Reporting, admin analytics and live updates evidence

Verified 2026-10-13 in `/workspace/PATHABLE`, locally saved and uncommitted on unborn `work`. The user authorized Phase 4, paused it, then resumed it. Authorization ends at this phase. Scheduled model/effort: GPT-6.1 Sol / High; exact runtime identity is unverified. No commit, push, deployment or environment publication occurred.

## Final checks

| Command from repository root | Actual result |
| --- | --- |
| `bash scripts/test.sh` | Ruff and formatting passed; **303 pytest tests passed**, no failures/skips/xfails, 59.38s; one Starlette/httpx dependency deprecation warning |
| `bash scripts/test_frontend.sh` | Generated API drift, TypeScript, ESLint, Prettier and production build passed; **38 Vitest tests in 9 files** passed (4.35s); **18 live Playwright tests** passed (1.4m), one worker, no retries/skips |

Backend breakdown: 163 pure-routing tests, 42 routing integration tests, 37 earlier backend/CLI tests and 61 new Phase 4 tests (21 reporting, 17 evidence, 15 events/analytics, 8 runtime). Frontend tests extend the earlier 22 with streaming, event-hook, FormData and live-route-currentness coverage. Browser coverage includes the earlier account/map/infrastructure/routing workflows and six real reporting/live-update cases.

Final logs are ignored local artifacts: `/tmp/pathable-phase4-backend-final.log` and `/tmp/pathable-phase4-frontend-final.log`. Browser output also contains harmless FORCE_COLOR/NO_COLOR notices and the expected reduced-motion notice. Screenshots `.local/screenshots/phase4-admin.png` and `phase4-mobile-reports.png` were inspected: real queue/analytics/audit data, readable desktop tables, persisted mobile report/history, and no horizontal page overflow in the mobile browser assertion. This is scoped visual/keyboard coverage, not a whole-system accessibility audit.

## Critical acceptance evidence

| Gate | Executed evidence |
| --- | --- |
| B | Real browser submission and normalized private photo → admin verification → committed restriction/revision → SSE retirement of the chosen route → admissible recalculation with profile retained and explicit confirmation. Both directional arcs of a restricted physical edge are excluded in backend tests. |
| E | Normal users receive 403 on review with no mutation; another owner receives 404 for reports/images. Role revocation after initial authentication is rechecked inside the locked mutation transaction. |
| J | Real decoder subprocess tests reject fake MIME/signatures, SVG/archive/truncated/animated/oversize/over-pixel inputs and traversal attempts. Actual multipart bytes are bounded even with absent/false Content-Length. Tests cover CSRF, private reads, mode-600 normalized metadata-free files, slot/storage quotas, concurrent uploads, timeouts and pending-only deletion. |
| K | Independent concurrent opposing reviews yield one success and one 409; identical concurrent requests replay the same committed result. Injected precommit failure rolls back report/history/restrictions/audit/version/event/idempotency. Resolving one of two hazards preserves the other and baseline closure. A stale browser review retains its reason and cannot duplicate restrictions. |
| L | Committed events replay after a lost connection; expired/future/invalid/missing/gapped cursors reset. Duplicate/late events, identity changes, heartbeat loss, revision bursts and aborted requests cannot restore old guidance. Real offline interruption hides guidance; reconnect at the same version revalidates and requires confirmation. No route-result cache exists. |

The final connected browser measured **995 ms** from submitting verification to the client retiring the old route (target <2s). This includes request/commit/poll/client work for one synthetic scenario; it is not a concurrent-load latency guarantee. The 2k/5k routing benchmark remains historical Phase 3 evidence and was not rerun.

## Data, migration and operations

Migration `0002_reporting` adds seven tables (22 total), immutable report content/restriction sources, same-campus spatial/reference guards, deferred verified-report/restriction consistency and completed-idempotency guards. A real upgrade from the foundation preserves an edited edge and creates a reporting-semantics reset revision. Report decisions use one database-generated timestamp for status/history/audit/state/event. History remains append-only; only the owner maintenance role can remove graph events older than seven days, never update them or delete recent ones. Application-role UPDATE/DELETE stays revoked.

Analytics tests verify physical-edge/report grain, overlapping restrictions/evidence without multiplied counts, current stock versus `[from,to)` flow, window boundaries, UTC resolution days, empty means and zero-denominator null coverage. No hardcoded dashboard counters are used. Stream admission tests cover three per identity, 200 global and expiring leases; the configured caps are not measured server capacity.

Upload tests use temporary private directories. Browser fixtures use a UUID-named disposable PostGIS database and private upload directory, removed on graceful teardown. The auto-fixture resets only that disposable database's rate buckets between independent scenarios; production quotas remain enabled and backend controlled-clock tests separately exercise the actual 10-report/hour and 20-upload/hour limits with correct Retry-After. Development data is untouched.

Earlier failures were investigated and fixed: stale pre-Phase-4 expectations, a retention fixture trying to UPDATE immutable events, stale UI confirmation, stream abort handling, resumed empty replay waiting behind the proxy, and early endpoint selection before locations loaded. The retention fixture now inserts old committed rows in its isolated database; immutability checks were preserved. Assertions were retained and the final full suites have no unresolved failures.

## Scope and remaining checks

Only fictional `synthetic_demo` campus data is present. ML/datasets/weights/evaluation remain Phase 5; critical F is unrun. Full accessibility/security audit, production serving/capacity, scheduled owner maintenance, evidence backup/restore and release privacy policy remain Phase 6/7. Decode resource limits reduce risk but are not a general malware sandbox. Fresh-task file/volume restoration and macOS execution remain unverified. Existing Phase 1 retained-volume persistence evidence was not repeated during Phase 4.

## Installation, startup and saved environment

- `bash scripts/install.sh` exited 0: hash-verified Python dependencies, `npm ci` (378 packages), healthy retained PostGIS, migration/runtime grants and preserve-existing seed. Log: `/tmp/pathable-phase4-install-final.log`.
- The checkout-owned API/UI were stopped before refresh, then `bash scripts/start.sh` exited 0: DB health, current migration, preserved seed, owner maintenance, real API/routing checks, direct SSE reset, compiled UI/proxy and immediate resumed SSE keepalive. Log: `/tmp/pathable-phase4-start-final.log`. No DB volume reset or DB restart occurred.
- `pip check`, scoped Ruff/format for the changed browser/evidence-stream helpers, shell syntax checks, nonignored Markdown links/whitespace/JSON and `git diff --check` passed. The explicit scan covers 211 nonignored files, compensating for an unborn repository's empty tracked diff; OpenAPI has 42 operations/38 paths. Generated migration SQL trailing whitespace and helper import ordering were corrected without semantic changes.
- Read-only cleanup inspection found zero disposable test/E2E/upgrade databases, zero remaining browser upload directories and zero stream leases after smoke teardown.
- Complete `install_script` and Phase 4 `start_skill` are confirmed saved in the cloud draft (`status=saved`, `requires_publish=true`). Unrelated repository/network/secret settings were preserved. Review and save the draft in environment settings, then publish to activate reuse. Saving does not execute or publish configuration; fresh-task restoration was not tested.

An exploratory Ruff check outside the configured backend target found older helper shebang/style differences and the browser helper's import order. The import order was fixed; legacy helpers were preserved, and scoped changed-helper checks pass. This broader exploratory check is not claimed as a passing repository-wide formatting gate.
