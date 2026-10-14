# Phase 6 — Integration, security and defect fixing

Verified on 2026-10-13 in `/workspace/PATHABLE`, with locally saved, uncommitted files on unborn `work`. Phase 6 was authorized by “continue” after the Phase 5 handoff. Scheduled model/effort: GPT-6 Astra / High; runtime identity is unverified. No commit, push, deployment or environment publication.

## Reproduced defects and repairs

1. An administrator demoted, disabled or auth-version-revoked after request authentication could still mutate infrastructure. Three new real-DB regressions reproduced successful unauthorized edits. Graph edits now use the same fresh, transaction-locked actor validation as report/prediction review, before graph locking. Rejected edits leave the edge, revision, audit and events unchanged.
2. Evidence reservation, decoded-image publication and deletion could proceed after account revocation. Three additional regressions reproduced the defect. Reservation now combines fresh authorization with the existing exclusive user quota lock; publication rechecks after decoding and rejects/releases the reservation if authorization changed; deletion rechecks before touching state/content. Temporary files are removed and a refused deletion preserves ready evidence. Concurrent quota tests still pass.
3. A non-ASCII CSRF header raised a TypeError instead of 403. It now follows the normal invalid-token path. Early body-size/media-type rejections omitted no-store, nosniff and the response request-ID header; they now use the normal response boundary.
4. Recharts made hidden chart elements keyboard-focusable. The initial authenticated axe scan failed `aria-hidden-focus`. Charts now disable that redundant accessibility layer while retaining visible equivalent count lists/tables. Dialogs without descriptions no longer reference a nonexistent description.

The first six security regressions failed before repair. The first evidence race run failed all three cases. An intermediate security rerun exposed an incorrect new-test assumption that seeded GraphEvent count was zero; the assertion now compares against its actual pre-mutation count. Final targeted security/evidence validation passed **27 tests**. The first accessibility run passed the public scenario and failed the authenticated scenario; both passed after the chart fix. No assertion or accessibility rule was disabled to obtain passing results.

## Full validation

| Command from repository root | Final result |
| --- | --- |
| `bash scripts/test.sh` | Ruff/format passed; **330 backend tests passed**, 121.03s; no failures/skips/xfails, one existing Starlette/httpx deprecation warning |
| `bash scripts/test_frontend.sh` | OpenAPI drift, TypeScript, ESLint, Prettier and production build passed; **41 component tests in 10 files**, 7.91s; **22 full-stack browser tests**, 2.6m, one worker, zero failures/skips/retries |
| `bash scripts/test_ml.sh` | Ruff/format and **10 actual CPU pipeline fixture tests passed**, 2.71s; no failures/skips |
| `bash scripts/install.sh` then `bash scripts/install_ml.sh` | Frozen core/npm/optional CPU installs passed; both environments pass `python -m pip check`; configuration and existing data preserved |

Backend adds ten new regressions to Phase 5's 320. Browser adds two accessibility scenarios and one security scenario to Phase 5's 19, and extends populated reporting/annotation scenarios with axe checks. Final browser rerun uses the evidence authorization repair. Logs: `/tmp/pathable-phase6-backend-final.log`, `/tmp/pathable-phase6-frontend-final.log`, `/tmp/pathable-phase6-ml-tests.log`, `/tmp/pathable-phase6-install.log`. Browser color-environment/reduced-motion notices are informational.

The connected report scenario measured **1141 ms** from the verification request to removal of the obsolete route overlay. This is one synthetic scenario, not a load guarantee. Optional CPU fixture training/evaluation is execution evidence only; real hazard training/evaluation remains unrun for lack of approved resources.

`.venv/bin/python scripts/dev.py stop` followed by `bash scripts/start.sh` loaded the current backend and passed direct API/routing/SSE/ML and compiled-UI/proxy/resumed-SSE smokes. `.venv/bin/python scripts/verify_persistence.py` then restarted only the owned API and Compose DB, retaining its named volume. User/session/profile/saved destination/graph survived; the temporary persistence account was removed. A subsequent `bash scripts/start.sh` passed the same functional smokes again. Logs: `/tmp/pathable-phase6-start.log` and `/tmp/pathable-phase6-persistence.log`. ML remained DISABLED throughout.

## Security and dependency scope

Real browser tests use the actual same-origin Vite proxy, isolated API/PostGIS database and cookies. Checks cover missing CSRF, hostile Origin, token rotation, HttpOnly/SameSite, cross-account report/prediction denial, ordinary-user review denial, plain-text report rendering and logout access denial. Existing tests cover private evidence ownership, hostile image bytes, stale report review, constraint/currentness failures and offline recovery. A refused database connection during an authenticated write returns redacted 503 and persists no edit. Both development and E2E Uvicorn helpers explicitly disable forwarded-header trust.

`npm audit --json` reported zero advisories. `pip-audit 2.10.1` checked the fully pinned core lock with `--no-deps --disable-pip`: 41 entries, zero advisories, none skipped. The optional ML lock contains 13 entries; the direct PyTorch URL was skipped by the tool, so a separate `torch==2.14.1` advisory query was executed successfully with no findings. This checks the wheel's declared upstream version, not its binary internals. The actual wheel remains hash-verified by installation. See [audit snapshot](examples/phase6-dependency-audit.json). OS/container scanning and production TLS/proxy/header configuration remain release work; zero package advisories is not a penetration-test result.

## Accessibility scope

Pinned `@axe-core/playwright` runs WCAG 2 A/AA and 2.1 A/AA rules without exclusions. Audited desktop public landing/navigation/report/login/register screens, the same screens at 320 CSS pixels, mobile navigation dialog, signed-in dashboard/preferences/admin, infrastructure editor, populated report review and analytics, owner report history and synthetic annotation review. Keyboard dialog dismissal restores focus to its trigger; existing keyboard search, mobile navigation, reduced-motion and text/map equivalence tests pass. Public reflow checks detect horizontal overflow at 320 pixels. The current admin screenshot was visually inspected, including populated chart/table alternatives and audit entries.

This is not complete WCAG certification. Manual assistive-technology review, physical-device testing and production-browser combinations remain unrun. Synthetic annotation fixtures test UI/review behavior only, not hazard classification quality.

## Routing measurement

`.venv/bin/python scripts/benchmark_routing.py` executed 20 sequential calculations over a synthetic graph with 2,000 nodes, 5,000 physical edges and 10,000 directed arcs. Five origin/destination cases per algorithm/alternative setting; Python 3.12.14, five visible logical CPUs, four-CPU cgroup quota and 32 GiB memory limit. The shared cloud host was also refreshing installation, so these observations are not isolated capacity measurements. Timing includes validation/filter/search, excludes HTTP/DB. All primary costs agree between Dijkstra and A*.

| Algorithm | Alternatives requested | Median ms | Observed nearest-rank P95 ms |
| --- | --- | --- | --- |
| Dijkstra | 0 | 89.70 | 98.92 |
| A* | 0 | 72.51 | 96.51 |
| Dijkstra | 2 | 809.08 | 1661.47 |
| A* | 2 | 348.84 | 384.21 |

Each of the ten requests for alternatives reports bounded/incomplete alternative search. Proven primary results are retained; exhaustion is not concealed. Dijkstra's observed alternative P95 exceeds the planning target of 1.5 seconds. No correctness budget or hard constraint was relaxed, and no speculative engine rewrite was made. A* remains the faster tested option. Five samples per group cannot establish a reliable population percentile or production throughput. See [raw benchmark](examples/phase6-benchmark.json).

## Critical A–L coverage

| Gates | Executed coverage |
| --- | --- |
| A, C, D, G, I | Pure routing independent oracle/generated graphs; route API constraints/unknowns/no-route; real browser preferences, alternative/totals/geometry/text and same-node flows |
| B, K | Real private image/report → administrator verification → source-specific restriction → graph event → retired route → confirmed reroute; independent CAS/idempotency and multi-report ledger transactions |
| E | API/browser nonadmin review rejection, fresh role revocation and unchanged audit/restriction/graph checks |
| F | Real DB/API/browser annotation acceptance leaves route eligibility unchanged; explicitly synthetic compute fixture, no available trained hazard model |
| H | Actual API plus DB-container restart retaining named volume; user/session/profile/saved destination/graph survive and temporary account is removed |
| J | Real bounded image decoder, MIME/byte/pixel/path/quota/privacy checks, plus account revocation during upload/publication/deletion |
| L | Repeatable-read/revision/expiry retry checks, SSE replay/reset/disconnection/offline/resume, client cancellation/retirement and no stale overlay; no route cache exists |

## Remaining release limits

ML remains disabled: no licensed, approved hazard dataset or evaluated product weights. Campus geometry is fictional `synthetic_demo`. Production serving/TLS/security headers, trusted proxy configuration, CI/release workflows, coordinated DB/evidence/model backup restoration, monitoring/capacity and fresh-task restoration remain Phase 7 work. Retained-container restart is not backup restoration. There is no claim of production navigation readiness or a complete external security audit.

## Saved configuration and repository checks

The complete tested `install_script` (core plus optional CPU installation) and `start_skill` were saved and read back at draft revision **7**, with `status=saved` and `requires_publish=true`. Repository membership, network policy and secret requirements were preserved. Review/save in environment settings, then publish; no publication or new-task restoration was performed.

Whitespace/JSON/local Markdown links passed across **251 nonignored files**, including untracked source; `git diff --check` also passed, but alone cannot validate this unborn checkout. Read-only cleanup checks found zero disposable test DBs, zero temporary ML test roles and zero development model/job/prediction rows. A cleanup query initially used the wrong stream-lease table name; this was a verification-command error, corrected using the ORM model's actual table name.
