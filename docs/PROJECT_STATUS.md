# Project status

Updated: 2026-10-14 (Asia/Kolkata). **Phase 8 independent final engineering audit is complete for the controlled synthetic demonstration and locally verified release candidate.** The user authorized it with “continue” after Phase 7; authorization ends at Phase 8. Trained ML remains unavailable and public navigation readiness is not established. Files are saved locally and uncommitted on unborn `work`; no commit, push, public deployment or environment publication occurred. See the [final audit](FINAL_ENGINEERING_AUDIT.md) for every success criterion, repaired findings and exact evidence.

## Implemented and verified

Phase 1 provides real FastAPI/PostgreSQL/PostGIS, cookie sessions/CSRF/Argon2, ownership/roles/rate limits, profiles/saved destinations, spatial integrity, authorized graph edits, transactional revisions/audit/events, observation expiry and persistent synthetic seed. Phase 2 provides the locked React/TypeScript UI, original branding, desktop/mobile map and text views, real account/preferences/saved-place flows and infrastructure administration. Session bootstrap and unsaved-profile draft guards remain. See [Phase 1 evidence](PHASE1_TEST_EVIDENCE.md) and [Phase 2 evidence](PHASE2_TEST_EVIDENCE.md).

Phase 3 adds pure constrained Dijkstra/A*, validated ECEF heuristic, bounded loopless Yen alternatives, independent exhaustive-oracle tests and coherent repeatable-read PostGIS route snapshots with final revision/expiry checks. Primary budget exhaustion is an error; bounded secondary exhaustion retains the proven primary and says alternatives are incomplete. The UI shows exact backend geometry, directions, totals and uncertainty. No route cache/history exists. Its 2k-node/5k-physical-edge benchmark is historical [Phase 3 evidence](PHASE3_TEST_EVIDENCE.md).

Phase 4 adds:

- Real owner-scoped reports/history and private JPEG/PNG evidence with bounded decoding, normalized metadata-free files, quota reservations and pending-only deletion.
- Transactional admin verification/rejection/resolution with expected versions, canonical idempotency, source-specific physical-edge restrictions, append-only history/audit and the shared graph revision/event service. Role freshness is rechecked in the mutation transaction. Resolving one hazard preserves others and baseline availability.
- Durable cookie-only SSE replay/reset, bounded frames/leases, heartbeat monitoring and reconnect validation. Known graph changes retire route guidance immediately, preserve trip/profile, cancel superseded requests and require explicit confirmation of the recalculated route. Ten-second route polling remains a fallback.
- Database-backed admin stock/flow analytics, category/resolution charts with tables, mapped-length coverage and paginated audit history. Review drafts retain their original version through background refreshes.
- Safe reporting migration to 22 tables, owner maintenance for old events/interrupted evidence, and real direct/proxied SSE startup smokes. The Phase 4 API had 42 operations/38 paths; Phase 5 now has 47 operations/43 paths.

Phase 5 adds the separate hash-locked CPU environment, licensed manifest/group/hash/perceptual leakage audit, deterministic conditional classifier training/evaluation, immutable safe-tensor asset registration, private leased inference jobs and human annotation review. Worker permissions exclude graph/restriction/evidence/review/model changes. Critical F passes through actual DB/API/browser review using labeled synthetic compute fixtures; no product model is enabled and no real hazard performance was measured. See [resource audit](ML_RESOURCE_AUDIT.md), [ML commands](../ml/README.md) and [Phase 5 evidence](PHASE5_TEST_EVIDENCE.md).

Decisions: [ADR-012](adr/012-phase3-routing.md), [ADR-013](adr/013-phase4-reporting.md). Exact Phase 4 checks and limits: [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md).

Phase 6 repaired stale administrator authorization on infrastructure edits, account revocation races around private evidence reservation/publication/deletion, malformed CSRF error handling, missing request-boundary security headers and hidden-chart keyboard focus. Shared authorization locks preserve graph/audit/event atomicity and quota concurrency. See [Phase 6 evidence](PHASE6_TEST_EVIDENCE.md).

## Evidence and cloud configuration

Final Phase 8 checks passed: **341 backend tests**, **10 separate CPU pipeline fixture tests**, **41 component tests**, **22 full-stack browser tests**, **22 operator-helper tests**, plus contract/type/lint/format/build and the full HTTPS/recovery/clean-source release wrapper. No final failures/skips/retries. Browser checks cover real proxy sessions/ownership/CSRF/plain-text rendering and automated accessibility across public, account, admin and populated review screens. Public 320-pixel reflow and keyboard dialog restoration pass. Historical Phase 6 package advisory scans found no published advisories; direct-wheel PyTorch was checked separately by version. This is not complete WCAG certification or an external penetration test.

Frozen core/optional installation has prior executed evidence; current owned service startup and direct/proxied API/routing/SSE/ML smokes pass. Critical H verifies user/session/profile/saved destination/graph across an owned API plus retained-volume DB restart, with temporary-account cleanup. The Phase 8 connected report scenario retired its route in 956 ms. The current 2k-node/5k-edge benchmark retained matching optimal primary costs, with primary P95 at most 106.9ms and alternatives P95 at most 501.3ms in five-case groups. All alternative searches hit the expansion cap and correctly reported incompleteness. The historical Dijkstra-alternative P95 of 1.66s exceeded the planning target; neither run establishes service capacity.

Complete install_script/start_skill are saved for review; publication and fresh-task/volume restoration remain separate actions. Review/save in environment settings, then publish when ready. Actual local release backup restoration has passed independently; it does not establish public deployment or fresh cloud restoration.

## Remaining capabilities and limits

| Capability | State |
| --- | --- |
| Architecture, backend/DB/auth/core APIs | Complete through Phase 1 |
| Frontend, branding, map and text UI | Complete through Phase 2 |
| Constrained routing, alternatives and coherent route API/UI | Complete through Phase 3 |
| Reports/private evidence/review/restrictions/analytics/live updates | Complete through Phase 4 |
| Dataset/weights/training/inference | P5 integration/pipeline tested; licensed data/evaluated product weights missing; inference disabled |
| Whole-system security/accessibility/integration | Phase 6 scoped checks passed; manual assistive technology and production controls remain |
| Production serving/CI/release/backup restore | P7 local HTTPS/offline candidate, prepared CI, actual coordinated restore/restart and clean source build verified; public deployment/hosted CI unrun |
| Final whole-project audit | Phase 8 complete; actual code/results mapped to all final criteria, six scoped findings repaired |

Phase 5 fallback integration checks pass. Actual hazard training/evaluation/inference remains blocked by missing approved resources. Campus data is fictional `synthetic_demo`, not verified university navigation or production readiness. Routing, decoding and streaming have explicit bounds; capacity, long-term privacy/retention, manual accessibility and encrypted off-host recovery still require release work. Coordinated local backup restoration is verified.

Phase 7 adds pinned offline API/UI images, non-root/read-only HTTPS runtime, explicit owner-only migration/maintenance operations, commit-pinned prepared CI, protected backup/restore and a clean source rebuild. Production testing repaired Leaflet SVG classes that development Strict Mode had masked. TCP DB readiness avoids the temporary initializer race. The full release wrapper passed including real private-image restoration and occupied-target refusal. See [Phase 7 evidence](PHASE7_TEST_EVIDENCE.md), [runbook](RELEASE_RUNBOOK.md) and [demo](DEMO_SCRIPT.md).

Hosted CI, bundled Chromium download under this proxy, remote clone/fresh cloud restoration and macOS remain unverified. Public proxy/client-IP admission, host/container OS audit, real TLS/DNS, encrypted off-host recovery, monitored capacity and manual assistive technology are still gates before public navigation use. The blocked Playwright domain is saved for review; current-instance system Chromium checks passed.

## Next handoff

Phase 8 repaired malformed cursor parsing, unexpected-error privacy/correlation headers, incomplete restore metadata validation, runtime file ownership during recovery, colliding DB role names and a transient process-identity startup race. Focused regressions, the whole application suite and rebuilt HTTPS/restore/clean-source checks passed. Actual root-to-non-root private-file readability and real owned-service stop/start/repeat-start were separately tested. See the [final audit](FINAL_ENGINEERING_AUDIT.md).

**No next phase is scheduled.** Stop for user-selected follow-up work. Further engineering audit/remediation can use **GPT-6 Astra / Extra High**, the same requested Phase 8 settings; actual runtime identity remains unverified. See [continuation guidance](MODEL_SWITCH_GUIDE.md). Preserve safety/privacy/currentness and honest unavailable ML. Commit, push, public deployment and environment publication require separate direction.
