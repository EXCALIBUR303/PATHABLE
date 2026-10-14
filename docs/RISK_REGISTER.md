# Risk register and technical assumptions

Phase 0 baseline with implementation updates below; owners are implementation phases, not named people. Severity refers to impact if unmitigated. Status “planned” means the mitigation is designed, not implemented.

| ID | Risk / failure | Severity | Mitigation and observable acceptance | Owner / state |
| --- | --- | --- | --- | --- |
| R01 | Prohibited or unknown edge appears accessible | Critical | Strict hard filtering, nullable facts, current verification, tests A/C/G | P3 / planned |
| R02 | A* overestimates after unit/cost change | Critical | ECEF lower-bound invariant, nonnegative versioned cost, exhaustive/generated comparisons D | P3 / planned |
| R03 | Concurrent review or resolving one hazard erases another | Critical | Restriction ledger, lock order, CAS, idempotency and K | P4 / planned |
| R04 | Stale route survives graph change/event loss | Critical | Atomic graph events, expiry/version checks, replay/reset, no initial result cache, B/L | P1/P3/P4 / planned |
| R05 | Synthetic map mistaken for surveyed Woxsen data | High | Persistent data_origin banner, provenance in API/export, no university verification claim | All / fixture labeled |
| R06 | Account/ownership bypass or stolen session | Critical | Server RBAC, sessions/CSRF, object scoping, rate limits, E and negative tests | P1/P6 / planned |
| R07 | Malicious/decompression-bomb evidence upload | High | Byte/pixel/quota bounds, decoder isolation, re-encode, private storage, J | P4/P6 / planned |
| R08 | AI overclaim, leakage or unsuitable data/license | High | Dataset/model cards, held-out grouped splits, real weights only, human verification, F | P5 / data unresolved |
| R09 | DB unavailable or migration destroys data | High | Real PostGIS tests, 503 honesty, transactional seed, backup/restore, H | P1/P7 / planned |
| R10 | External basemap/network/paid-service dependence | Medium | Geometry-only default, optional attributed tiles, text fallback | P2 / planned |
| R11 | Inaccessible map-only UI | High | Text route/list parity, keyboard interactions, focus/reduced-motion and manual checks | P2/P6 / planned |
| R12 | New dependency versions/ARM database image incompatible | Medium | Metadata checked; install locks/builds and image-manifest checks remain phase gates; documented amd64 fallback | P1/P2 / unresolved runtime validation |
| R13 | Alternative route search becomes costly | Medium | K<=3, 20 candidates, expansion/time budgets; no fake no-route on timeout | P3 / planned |
| R14 | Analytics duplicates or misleading coverage | Medium | Physical-edge/report grain, explicit denominators, zero-denominator null, aggregation fixtures | P4 / planned |
| R15 | Privacy leaks in images, logs or future deployment | High | EXIF removal, private evidence, no route history, retention/public-release review | P4/P6/P7 / planned |
| R16 | Observation aging does not trigger reroute | High | next_expiry_at, serialized expiry transaction, client valid_until and clock-controlled tests | P1/P3/P4 / planned |
| R17 | Phase summaries overstate implementation or tests | High | Actual file/test inspection, phase-gated status, exact evidence, no automatic next phase | All / enforced in Phase 0 |

## Explicit assumptions

- A01: The user authorized Phase 8 after Phase 7. The independent final audit includes scoped repairs and validation; authorization ends at this boundary. No commit, push, public deployment or publication is authorized.
- A02: First application serves a single fictional campus with a modest graph (initial planning target <=2,000 nodes and <=5,000 physical edges). Larger graphs require benchmark evidence before broader claims.
- A03: Routing uses chosen access-point nodes. Continuous GPS guidance, emergency routing, indoor floor plans and automatic image geolocation are outside initial scope.
- A04: Infrastructure observation validity is currently a fixed 30-day policy identified by `accessibility-v1`. Changing it requires a reviewed code/policy-version change; no runtime configuration knob is implemented. This is an engineering default requiring real operators to set an appropriate survey policy, not a regulation.
- A05: Default wheelchair constraints (8% grade, 0.9m width) are customizable preferences, not assertions of legal compliance or individual suitability.
- A06: Same-origin browser deployment permits cookie sessions. Native apps/third-party API access would need a separate authentication design.
- A07: One API instance and DB-first events suffice initially; horizontal scaling needs shared evidence storage and measured DB connection limits.
- A08: PostgreSQL/PostGIS via Docker Compose is required in development/CI. Docker/Compose, PostgreSQL/PostGIS and locked application dependencies are installed and validated through Phase 4; fresh-task volume restoration remains unverified.
- A09: Available datasets, licenses, weights and compute for ML are not established. No missing key blocks architecture; assess in Phase 5 without blocking core navigation.
- A10: The scheduled Phase 8 model/effort is GPT-6 Astra / Extra High. The assistant has no tool that verifies or changes the active model/effort; records distinguish the requested schedule from verified execution metadata.

Phase 1 update: authentication/CSRF/ownership/rate-limit foundations (R06), real PostGIS migrations/persistence/rollback (R09), dependency/image checks (R12), graph CAS/audit/revision and expiry primitives (R03/R04/R16) now have executed evidence. Their report/routing/release portions remain pending. The selected DB image is confirmed amd64-only; Apple Silicon uses explicit emulation. See [Phase 1 evidence](PHASE1_TEST_EVIDENCE.md) rather than treating every planned mitigation above as implemented.

Phase 2 update: persistent synthetic provenance (R05), geometry without external tiles (R10), keyboard endpoint search and complete text pathway/location views, mobile focus restoration and reduced motion (R11), and frozen npm installation/build checks (R12) now have executed evidence. Live account/profile/saved-place and ordinary-user/admin browser checks extend R06. CSRF remains in memory; private responses are removed on logout. Profile edits retain their own version and draft so background updates cannot silently overwrite changes. Full screen-reader/axe/contrast/reflow audits and production security remain Phase 6/7 gates. See [Phase 2 evidence](PHASE2_TEST_EVIDENCE.md).

Phase 3 update: hard filtering and nullable/current facts (R01), independent-oracle/ECEF comparisons (R02), snapshot/final validation and client expiry/version checks (R04/R16), bounded alternatives and truthful budget outcomes (R13), exact route geometry/text/metrics on desktop/mobile (R11) now have executed evidence. The optional-auth connection is released before independent snapshot sessions; ten simultaneous route calls pass without pool starvation. Graph geometry is bounded before JSON transfer. No route cache exists. Ten-second polling leaves a discovery interval; SSE and event-to-client latency remain P4. All ten dense-graph alternative benchmark runs reached a limit, correctly marking incomplete search while retaining proven primary routes. See [Phase 3 evidence](PHASE3_TEST_EVIDENCE.md).

## Before real-campus or public use

Require permission and surveyed provenance for real campus data; measure geometry, widths, slopes and connections; define operators and review freshness; determine privacy/retention policy and incident response; assess capacity/accessibility/security; test restoration and service monitoring. These are release conditions, not permission requests for Phase 0. No production-readiness claim is made.

Phase 4 update: R03 source-specific closure/CAS/idempotency and rollback, R04/R16 durable live replay/currentness/expiry, R07 decoder/privacy/quotas and R14 physical-edge/report aggregate grain now have actual [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md). A connected browser observed 995 ms report-to-guidance retirement; concurrent capacity is unmeasured. R15 private metadata-free evidence is implemented, while account export/deletion/long-term privacy policy and backup restoration remain release requirements. No automatic AI routing effect exists; R08 awaits Phase 5 resources and critical F.

Phase 5 update: R08 now has a concrete resource audit, rights/group/hash/perceptual gates, safe tensor registry, restricted leased jobs, honest unavailable UI/API and executed critical F proving prediction review cannot affect routes. Real class quality/generalization/metrics remain blocked by absent approved assets. CPU fixture execution is not model performance. The optional Linux CPU lock installs with hash verification; Mac/runtime capacity and asset restoration remain unverified. See [Phase 5 evidence](PHASE5_TEST_EVIDENCE.md).

Phase 6 reproduced and fixed stale authorization on graph edits/evidence operations, malformed-CSRF errors, missing early rejection headers and hidden-chart focus. Package advisory checks found no published advisories, with direct-wheel PyTorch checked separately. Automated accessibility and keyboard/reflow scenarios pass; manual assistive-technology and production release checks remain. The benchmark has only five cases per group and observed Dijkstra alternatives above the 1.5-second target; bounded alternatives remain explicitly incomplete. See [Phase 6 evidence](PHASE6_TEST_EVIDENCE.md).

Phase 7 local candidate checks include actual coordinated private-image/database restore/restart and a clean source build; CI is prepared/linted but not remotely executed. Native system Chromium works; the bundled download was blocked at its CDN and the domain is saved for review. Build admission/scoped cache cleanup addresses measured disk exhaustion. Public proxy admission, host/OS audit, real TLS/DNS, encrypted off-host recovery, load/monitoring and manual assistive technology remain gates before public operation. See [Phase 7 evidence](PHASE7_TEST_EVIDENCE.md).

Phase 8 independently reviewed source and reproduced malformed cursor/server-error header gaps, incomplete backup metadata validation and colliding role configuration. Recovery ownership was also repaired and checked with a real root-to-non-root file probe. Startup helpers now wait for the expected process command before recording ownership; regressions and real restart/repeat-start checks preserve refusal to signal mismatched processes. See the [final audit](FINAL_ENGINEERING_AUDIT.md) for findings, final criterion mapping and current executions. R01–R04/R06/R07/R09/R13/R14/R16 now have local executed mitigations rather than only Phase 0 plans. R08 trained hazard quality, R11 manual accessibility, R12 non-Linux portability, R15 long-term privacy/off-host recovery and public operational capacity remain unresolved. The faster current benchmark does not establish a service-capacity guarantee or erase earlier target misses.
