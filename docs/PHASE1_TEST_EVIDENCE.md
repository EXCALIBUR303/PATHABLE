# Phase 1 execution evidence

2026-10-12. Root `/workspace/PATHABLE`; backend commands run in its `backend/` directory. Git: unborn work, locally saved files, no commit/push/deployment. Python 3.12.14; PostgreSQL 17.5/PostGIS 3.5; Docker 28.4.0/Compose v2.40.3.

## Actual commands and results

| Command / directory | Actual result |
| --- | --- |
| `.venv/bin/pip-compile --cache-dir="$PWD/.local/pip-tools" --generate-hashes --resolver=backtracking --output-file=backend/requirements.lock backend/requirements.in` (root, workspace PIP_CACHE_DIR) | Hash lock generated; TLS/artifact verification retained |
| `.venv/bin/pip install --require-hashes -r backend/requirements.lock` (root) | Selected stable dependencies installed with hash checks |
| `bash scripts/install.sh` (root), repeated | Exit 0; DB healthy, migrations/grants applied, existing campus preserved |
| `../.venv/bin/python -m app.cli seed --synthetic` (backend), repeated | Exit 0, no duplicates/overwrites |
| `../.venv/bin/pytest -q --tb=short` (backend) | **35 passed**, 0 failed/skipped, 1 upstream warning; 12.25s final core run |
| `../.venv/bin/pytest app/tests/integration/test_cli.py -q --tb=short` (backend) | **2 passed**, 0 failed/skipped, 1 upstream warning; 1.69s, separate run of newly added CLI tests |
| `../.venv/bin/ruff check app alembic` and `../.venv/bin/ruff format --check app alembic` (backend) | Exit 0; newly added CLI file separately checked/formatted |
| `.venv/bin/ruff check --config backend/pyproject.toml scripts/configure_local.py scripts/dev.py scripts/smoke_api.py scripts/verify_persistence.py` (root) | Exit 0 |
| `bash -n scripts/install.sh scripts/start.sh scripts/test.sh` (root) | Exit 0 |
| `.venv/bin/python -m pip check` (root) | Exit 0, no broken requirements |
| `../.venv/bin/python -m app.cli export-openapi` (backend) | Exported OpenAPI; separately asserted exact equality with app.openapi(), **29 operations / 26 paths** |
| `bash scripts/start.sh` (root), repeated | Exit 0; DB/migration/seed readiness, owned API start/reuse and functional HTTP smoke |
| `.venv/bin/python scripts/smoke_api.py` (root, also called by startup) | Live readiness, synthetic campus, 13 measured edges, access points, anonymous session passed |
| `.venv/bin/python scripts/verify_persistence.py` (root) | Exit 0; actual API/Compose DB restart, retained volume, user/session/profile/destination/graph survived; successful test account cleaned up |
| `git diff --check` (root) | Exit 0; new files separately inspected |

Pytest creates a new UUID-named pathable_test_* database, migrates it from empty with real PostGIS, resets only that database between tests and drops it afterward. Development data is preserved. Repeated installation upgrades at head without reset. These are real database tests, not SQLite or fake adapters.

## Verified behavior

Authentication/ownership: normalized email uniqueness including concurrent registration; forbidden role assignment; cookie flags/hashed sessions; exact Origin/CSRF; password whitespace; rotation/logout/idle and absolute expiry/inactive/auth-version invalidation; durable failed-login limits; body/media/JSON checks and input redaction; profile/name CAS; saved destination ownership; secure CLI admin creation/login/audit and noninteractive/duplicate refusal.

Graph/database: GeoJSON and PostGIS metre distances; NULL unknowns; search/cursor scope/bbox/access-point mappings; ordinary-user admin refusal; create/edit/retire; optimistic and concurrent updates; atomic audit/revision/event; geometry rollback and incident geometry requirements; cross-campus FK/nonfinite rejection; remeasurement invalidates old verification; expiry bumps once; repeat seed protects edited data; runtime role cannot create schema or update/delete history. A real failed DB connection produces structured 503 without exposing connection details.

Critical **H passed** via live requests and real service/container restarts. **E foundation passed** for current admin graph operations; full report-approval E belongs to Phase 4. **L foundation** is versioned mutation evidence; no route cache exists. Full routing/reporting/AI/frontend critical scenarios A–G/I–L remain unrun until those features exist.

## Failures diagnosed and fixed

- Read-only Docker/pip-tools caches moved into ignored .local. Verification stayed enabled.
- Temporary network restriction caused proxy failures during resolution; granted network capability restored the required operation. It was not a missing package/token.
- Initial shared PostGIS trigger referenced a nonexistent point-record field. Branch-specific trigger logic fixed it; failed seed transaction rolled back, and fresh migration tests passed.
- Initial startup probe treated TIME_WAIT as an occupied listener. SO_REUSEADDR fixed the probe; actual restart verification passed.
- Regression test found inherited password whitespace stripping. Credentials explicitly preserve whitespace; regression/core tests passed.
- A run overlapping intentional DB restart had 33 passes and 2 connection errors. Restart and pytest were sequenced; final core run passed all 35. Documentation now requires separate restart checks.

One remaining upstream warning: Starlette's test client deprecates httpx in favor of httpx2. No warning filter, disabled assertion or skipped test hides it. UI/browser/CI/production builds, uploads, routing, ML, release security, Mac execution, fresh-task/DB-volume restoration are unverified.

## Saved reusable configuration

Cloud save confirmed `status=saved`, `requires_publish=true`: complete **install_script** and **start_skill** written. Network/repositories/bindings preserved. Private local credentials are generated/preserved in ignored mode-600 .env; no values appear in the draft or documentation. Review/save in environment settings, then publish to activate reuse. Draft persistence does not imply publication, deployment or new-task validation.
