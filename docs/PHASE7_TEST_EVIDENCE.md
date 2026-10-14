# Phase 7 — Deployment preparation and documentation

2026-10-13, `/workspace/PATHABLE`, locally saved/uncommitted on unborn `work`. User authorized Phase 7 with “continue” after Phase 6. Scheduled GPT-6.1 Sol / Medium; exact runtime model/effort is unverified. No commit, push, public deployment or cloud publication.

## Implemented candidate

- Pinned Python 3.12.14, Node 24.19.0 and Nginx 1.30.5 base-image digests; hash-verified Python wheels and npm integrity cache; Docker RUN/build steps execute offline. Context excludes private configuration/uploads/weights/environments. Release targets Linux amd64.
- A separate Compose project, protected host storage, same-origin TLS/static production UI and unbuffered SSE. API/web are non-root/read-only, with CPU/memory/process/temp bounds. Release DB is not exposed on a host port. Runtime API has no owner credential; operator containers alone receive it.
- Explicit migration/seed/start/health/maintenance/admin commands, strong private fixture generation, public/private CA handling and production CSP/HSTS/frame/referrer/permission headers. Synthetic seeding is explicit; ML remains disabled.
- Coordinated PostgreSQL/private-evidence/model-storage snapshots with checksum/file-membership validation. Restore refuses occupied storage or non-pristine DBs, creates a missing DB from template0, imports transactionally and applies target credentials/grants. TLS/credentials remain separate secure operator recovery responsibilities.
- Commit-pinned GitHub Actions using the actual frozen/test/release wrappers, runbook/upgrade/rollback/maintenance guidance, deployment template, synthetic demo script and [ADR-015](adr/015-phase7-release.md).

## Reproduced problems and corrections

1. Build-network DNS could not resolve package hosts. Host prefetch preserves TLS/hash/npm integrity checks; named BuildKit contexts make Docker builds network-independent.
2. Copied source/Nginx configuration inherited restrictive host modes and was unreadable to non-root containers. Image COPY now sets explicit readable modes; private mounted keys/files remain protected.
3. A production-only Leaflet defect was hidden by development Strict Mode: pathOptions applied className after SVG creation. Classes now pass as initial layer options for lines/points. The component boundary mock was corrected, and the actual built-browser regression verifies the selected SVG and backend total. It passed without CSP violations.
4. The PostGIS initialization-only socket server could satisfy health before final startup. TCP health now waits for the final server. Restore initially collided with the image's pre-created tiger schema; bootstrap DB and application DB are separated, and pristine targets are created from template0 without cleaning existing data.
5. A validation run overlapped browser navigation and deliberate backup shutdown; browser validation was rerun alone. New smoke assumptions were corrected to the existing `selected_algorithm`/`alternatives_limit` and `graph.reset` contracts; no application contract was changed.
6. Repeated candidate builds exhausted disk through unused build cache and old image references. Only task-created caches/stopped fixture containers/unreferenced task images were reclaimed; volumes/private files/config/backups were preserved. Build admission now requires 8 GiB free. Validation reclaims exact newly generated cache IDs and copied dependency caches, and stops complete fixture stacks afterward.

## Executed regressions

| Command from repository root | Result |
| --- | --- |
| `bash scripts/test.sh` | Ruff/format; **332 passed**, 133.68s; zero failures/skips/xfails, one existing Starlette/httpx deprecation warning |
| `bash scripts/test_frontend.sh` | Contract/type/lint/format/build; **41 component tests**, 10.43s; **22 browser tests**, 3.0m, zero failures/skips/retries |
| `bash scripts/test_ml.sh` | **10 CPU fixture tests passed**, 4.27s; no failures/skips; not product hazard performance |
| `.venv/bin/pytest scripts/tests/test_backup_manifest.py -q` | **6 passed**; corruption/missing/extra/traversal/symlink rejection and valid membership checks; dummy dump bytes are never restored by these unit tests |
| `/tmp/pathable-actionlint/actionlint .github/workflows/ci.yml` | Passed using checksum-verified official actionlint 1.7.7 |
| `.venv/bin/python scripts/smoke_release_browser.py` | Passed through actual compiled HTTPS UI: SVG/route totals, real account/login/logout, Secure host cookie, no CSP violations; Python also verifies certificate chain/host/validity, headers/routes/DB/SSE |

Logs: `/tmp/pathable-p7-backend-final.log`, `/tmp/pathable-p7-frontend-final.log`, `/tmp/pathable-p7-ml-final.log`, `/tmp/pathable-p7-release-smoke.log`. The connected report scenario measured **776 ms** from verification request to old-overlay removal, one synthetic case rather than a load guarantee. Two new backend tests cover missing runtime owner credentials and weak optional owner rejection.

A running API assertion verified nonzero UID, no owner credential, no bundled `.env` and disabled ML. Private normalized image bytes are validated through actual HTTPS/DB/filesystem restoration; the model-storage probe is an inert labeled text file, not registered/evaluated weights. `bash scripts/test_release.sh` subsequently passed end to end (exit 0): eight-helper Ruff/format checks, six manifest unit tests, frozen artifact prefetch/offline images, strict HTTPS and built-browser routing/authentication, coordinated real account/profile/saved-place/report/private-image/graph/model-storage restoration, retained restart, populated-target refusal, and no-cache offline images from a clean source export with fresh migrations/seed/HTTPS requests. All created fixture services stop afterward; data/volumes remain retained. The full log is `/tmp/pathable-p7-release-final.log`. Earlier wrapper/clean attempts failed on disk capacity; final admission/cache cleanup and a full rerun resolved them. The no-cache source export contains no development `.env`, `.venv` or `node_modules`; it consumes separately verified dependency artifacts.

The actual restore retained normalized image bytes and hashes, unchanged graph features/revision and persistent user/profile/saved-place/report data. Target credentials differ and runtime role grants are reapplied. An inert labeled model-storage text probe was preserved without enabling/registering a model. See [result metadata](examples/phase7-release-validation.json). Buildx v0.31.0 and Compose v2.40.3 were used; older/macOS combinations remain unverified.

## Scope and remaining limits

The current cloud proxy rejected the Playwright Chromium download at `cdn.playwright.dev` with 403 Domain forbidden. System Chromium executed local checks. That exact host was added to the saved draft while preserving package-manager presets; runtime network changes and successful bundled-browser download are unverified. Hosted CI was prepared/linted, not run on GitHub; no push is authorized. The clean validation uses a local nonignored source export, not a remote clone or fresh cloud task.

Public DNS/certificate issuance/renewal, host/container OS audit, trusted client-IP admission (anonymous buckets aggregate behind Nginx), encrypted off-host recovery, deployment load/monitoring and manual assistive-technology review remain public-release/audit gates. All campus data is fictional `synthetic_demo`; trained hazard resources remain unavailable. These local results establish release preparation, not public navigation readiness.

## Reusable setup and current runtime

The complete sequence `bash scripts/install.sh`, `bash scripts/install_ml.sh`, `bash scripts/prepare_release_artifacts.sh` passed again, preserving private configuration/development data. The owned API was reloaded and `bash scripts/start.sh` passed DB readiness, live synthetic API/routes, direct/proxied SSE, explicit ML DISABLED and compiled frontend checks. Logs: `/tmp/pathable-p7-install-final.log`, `/tmp/pathable-p7-start-final.log`.

The complete installer/start instructions and the observed Playwright CDN addition are saved for review, with network presets/repositories/secret requirements preserved. Saving is separate from runtime activation/publication; review/save in environment settings, then publish when ready. Final draft readback is recorded in the handoff.

Final readback confirmed draft revision **10** with exact installation/start fields and preserved repository/secret requirements; the only custom network addition is `cdn.playwright.dev`. `requires_publish=true`: review/save, then publish as a separate user action. Whitespace/JSON/local Markdown link checks passed across **277 nonignored files**, including untracked source; `git diff --check` also passed. The production routing screenshot was visually inspected: selected SVG, backend-matching 44.4m/one-minute estimate, directions and fictional/currentness caveats.
