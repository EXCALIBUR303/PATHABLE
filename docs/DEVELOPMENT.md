# Full-stack development workflow through Phase 7

Prerequisites: Python 3.12, Node 24, Docker Engine/Desktop and Compose v2. Commands run from `/workspace/PATHABLE` in cloud, or the checkout root on a MacBook. The pinned PostGIS image is amd64-only, so Apple Silicon uses explicitly configured linux/amd64 emulation; macOS execution itself has not been tested here. `.python-version` and `.nvmrc` record tested versions, not automatic tool activation.

```sh
bash scripts/install.sh
bash scripts/start.sh
bash scripts/test.sh
bash scripts/test_frontend.sh
```

Installation preserves an existing `.env`, creates a private mode-600 local file if absent, creates/refreshes `.venv`, installs `backend/requirements.lock` with `--require-hashes`, starts the named-volume DB, applies migrations, configures the restricted application role and seeds only an empty synthetic campus. No destructive volume reset. Generated local credentials are for this developer-owned database, not external services; values are never printed. Injected matching bindings are reused by the configuration helper. Required local secrets are POSTGRES_PASSWORD, APP_DB_PASSWORD, CSRF_SECRET and RATE_LIMIT_HASH_KEY. Review `.env.example` for nonsecret settings; keep the populated file ignored.

Installation also verifies Node 24 and installs `frontend/package-lock.json` with `npm ci`. Startup restores DB process, applies safe pending migrations/role grants, preserves existing campus edits, starts the owned API and Vite frontend, and runs read-only checks for readiness, measured graph, access points, anonymous session, real Dijkstra/A* routing with reconciled totals, direct SSE reset, honest optional ML status, compiled React entry, same-origin proxy and resumed SSE heartbeat. It detects another listener instead of killing it. Live processes are not expected to survive snapshots. If project dependencies are absent, run installation first. Logs are in ignored `.local/api.log` and `.local/web.log`; PID metadata includes process identity so stop does not signal an unrelated PID. Default ports are API 8000, frontend 5173 and DB 5432; root configuration supports API_PORT/FRONTEND_PORT. APP_ORIGIN must match the browser origin exactly.

```sh
.venv/bin/python scripts/dev.py stop
.venv/bin/python scripts/web.py stop
.venv/bin/python scripts/smoke_api.py
.venv/bin/python scripts/smoke_routes.py
.venv/bin/python scripts/smoke_frontend.py
.venv/bin/python scripts/smoke_events.py
.venv/bin/python scripts/smoke_ml.py
.venv/bin/python scripts/verify_persistence.py
```

The persistence command deliberately restarts **this checkout's** API and Compose DB, retaining all volumes. Run it separately from pytest or other database operations. It creates a temporary account, logs in, saves a destination, restarts services, checks user/session/profile/destination/graph persistence, then removes its account on success. An interrupted check may leave a test-only account; inspect it before cleanup. Do not run it against someone else's production services.

## Backend administration

From `backend/`:

```sh
../.venv/bin/python -m app.cli prepare-db
../.venv/bin/python -m app.cli migrate
../.venv/bin/python -m app.cli seed --synthetic
../.venv/bin/python -m app.cli create-admin --email you@example.com --name "Demo Administrator"
../.venv/bin/python -m app.cli export-openapi
../.venv/bin/python -m app.cli maintenance
```

Admin creation requires an interactive terminal and prompts twice without echoing the password. It refuses an existing account rather than silently elevating it. There are no default admin credentials. Registration cannot select a role. Seed uses deterministic UUIDs and refuses to overwrite edited/incomplete seed records; `--if-empty` is a deliberate preserve-existing-data option for install/start scripts.

Use cookie sessions: fetch `/api/v1/auth/session`, retain its HttpOnly cookie and returned csrf_token, then send Origin equal to APP_ORIGIN and X-CSRF-Token on state-changing JSON mutations. The public read-only routing POST accepts a complete computational profile without login or CSRF and uses the existing durable 60/minute quota. Login rotates session and CSRF; use the new token. Logout revokes the session. The frontend uses a same-origin Vite proxy and in-memory CSRF. API endpoints are documented in generated [OpenAPI](openapi.json) and [API contract](API_CONTRACT.md). No user-facing loopback preview link is provided by cloud onboarding.

The owner DB account performs migration/role setup. Runtime uses `pathable_app`, with no schema creation and no audit/event UPDATE/DELETE. Owner credentials are local administrative settings, never returned in API responses. PostgreSQL is loopback-bound; production secrets, TLS, roles, backup/restore and deployment operations remain Phase 7 release work.

## Testing and dependency refresh

`bash scripts/test_frontend.sh` checks generated API contracts, strict TypeScript, ESLint, Prettier, Vitest, production build and Playwright. Playwright starts a separate API/UI on ports 18000/5174 against a fresh UUID-named `pathable_e2e_*` PostGIS database. Only this disposable database receives its fixture administrator. Shutdown drops that generated database and leaves the development campus/accounts untouched. Do not run multiple E2E suites concurrently or restart DB during them. Failure traces, screenshots and reports are ignored under `frontend/test-results`, `frontend/playwright-report` and `.local/screenshots`. They can contain test input; do not publish them without review.

This cloud host has `/usr/bin/chromium`; the config uses it unless PATHABLE_CHROMIUM_PATH selects another browser. On hosts without system Chromium, install Playwright's bundled browser, from `frontend/`:

```sh
export PLAYWRIGHT_BROWSERS_PATH="$PWD/../.local/playwright"
npx playwright install chromium
npm run test:e2e
```

The bundled-browser download and macOS execution were not tested here. Preserve the browser-path environment when running the root test wrapper. Keep browser/system-library installation checks enabled. `npm run api:generate` regenerates types after intentional OpenAPI changes; `api:check` only compares. `npm run dev` and `npm run preview` are manual alternatives to the owned frontend helper and require its port to be free. Read [frontend README](../frontend/README.md) and [Phase 2 evidence](PHASE2_TEST_EVIDENCE.md).

`bash scripts/test.sh` checks Ruff and executes pytest against a **new UUID-named pathable_test_* database**, independently migrates it, truncates only that generated database between tests and drops it afterward. It never truncates the development database. Integration tests use real PostGIS, including independent concurrent connections and database rollback/permission checks. Run restart verification separately to avoid disrupting test connections.

The Python lock includes runtime and development test tools. Installation/build caches are ignored under `.local`. To intentionally refresh after changing `backend/requirements.in`, use a separate lock-tool environment or install pip-tools 7.5.2 in `.venv`, then:

```sh
PIP_CACHE_DIR="$PWD/.local/pip-cache" .venv/bin/pip-compile --cache-dir="$PWD/.local/pip-tools" --generate-hashes --resolver=backtracking --output-file=backend/requirements.lock backend/requirements.in
```

Inspect the dependency change, install with hashes, run `pip check` and the relevant test suite. Do not bypass TLS/hashes or alter a checksum to silence a mismatch. Phase 0's design-check script is historical and intentionally checks that original scaffold; current readiness uses the executable commands above.

## Routing checks and benchmark

From the root, `.venv/bin/python -m pytest -c backend/pyproject.toml backend/app/tests/routing` runs the independent pure-engine suite without DB fixtures. `bash scripts/test.sh` also includes these tests and real-PostGIS route API tests. The standalone command `.venv/bin/python scripts/benchmark_routing.py` builds a deterministic synthetic 2,000-node/5,000-physical-edge workload and writes ignored `.local/routing-benchmark.json`. It measures graph validation/filter/search, excluding HTTP/DB, and reports incomplete alternative searches separately. This is a local measurement, not a capacity guarantee. See [Phase 3 evidence](PHASE3_TEST_EVIDENCE.md).

After editing API code, stop its owned process with `.venv/bin/python scripts/dev.py stop`, then run `bash scripts/start.sh`; the helper intentionally keeps an already healthy process instead of replacing it. Route results are not cached. Phase 4 SSE discovers committed graph changes through short one-second polls; ten-second route-version polling and focus/visibility/expiry checks remain fallbacks. Recalculated live routes require explicit confirmation.

## Private evidence and maintenance

Phase 4 accepts JPEG/PNG only: encoded file <=10 MiB, decoded pixels <=20 million, three processing/ready images per pending report and 100 MiB normalized user storage. Upload/delete require expected_version; report creation/review/resolution require UUID Idempotency-Key. The API authorizes before multipart parsing and caps actual streamed bytes. A separate Pillow subprocess normalizes orientation and strips metadata under CPU/address-space/output/time limits, with two decoders per API process. The Unix resource worker is verified here on Linux; macOS execution remains unverified.

Private normalized files default to ignored `.local/uploads` (`UPLOAD_ROOT` override resolves relative to the checkout). Directories/files use 0700/0600; no static upload route exists. Ready images require owner/admin authorization. Pending owners can remove evidence; verified evidence is retained. Keep database and private files together in future backups; restore validation remains Phase 7.

Startup runs owner maintenance; it can also be invoked explicitly with the backend CLI above. It removes expired idempotency/lease rows and graph events older than seven days, rejects processing uploads interrupted for over 24 hours, and cleans old unreferenced UUID files while preserving ready content. No production scheduler is implemented yet.

Each Playwright database has its own private upload directory and removes it on graceful teardown. An auto-fixture resets only that validated disposable database's rate buckets before each independent case; backend tests separately verify actual hourly report/upload limits. The production API's quotas remain enabled. Do not run browser suites concurrently or against development data. See [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md).

## Optional CPU ML (resource-limited Phase 5)

Core installation/startup needs no tensor packages or model assets. `bash scripts/install_ml.sh` creates a separate ignored CPU runtime, hash-verifies the ML lock, preserves/generates one local restricted-worker binding and prepares its DB grants without enabling analysis. `bash scripts/test_ml.sh` runs ten explicit synthetic execution fixtures. The optional lock supports Linux x86_64/Python 3.12 only; macOS ML is untested. See [ML README](../ml/README.md) for real manifest/training/evaluation/registration/worker commands and [resource audit](ML_RESOURCE_AUDIT.md) for missing assets.

Head is `0003_ml`; migration adds registry/jobs/predictions without changing graph revisions. Worker role permissions exclude authoritative graph/restrictions and evidence/review/model updates. Backend tests use a separate temporary UUID worker role/password, dropped after the test database, so optional installation is not required for core tests. ML status is unavailable by default; no synthetic model can be activated. Validated model assets, operator review, runtime configuration and a separately started worker are required for genuine asynchronous inference. Prediction acceptance is annotation-only. Normal routing/manual reports remain functional when ML is missing/failed.

Phase 6 adds pinned axe browser checks to `bash scripts/test_frontend.sh`, including 320-pixel public reflow and populated review/analytics states. Final evidence is [here](PHASE6_TEST_EVIDENCE.md). Run only one E2E suite at a time; run retained-volume restart checks separately from every DB test suite. The optional ML runtime remains disabled without approved evaluated assets.

Production candidate builds and coordinated recovery use a distinct Compose project; follow the [release runbook](RELEASE_RUNBOOK.md). They require Buildx/Compose features tested here at Buildx 0.31.0 / Compose 2.40.3 and at least 8 GiB free for build layers. The wrapper creates/stops isolated candidate projects and retains their volumes/private files, never resetting development data. OpenSSL 3 is needed for local fixture certificate generation. Mac release execution/optional CPU ML remain unverified; Apple Silicon needs amd64 Docker emulation, and native core development can skip the Linux-only ML install. The current cloud bundled Chromium download is blocked pending saved network review; system Chromium remains the verified local browser.
