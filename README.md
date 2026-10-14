# PathAble

**Every Path Should Be Possible.**

PathAble is a campus accessibility navigation platform combining verified infrastructure, personalized graph routing, community reports, and optional human-reviewed computer vision.

**Current state: Phase 8 final audit and local release checks pass; trained hazard inference remains unavailable.** Dijkstra and A* enforce explicit accessibility constraints, return bounded alternatives and backend geometry/instructions, and drive the real desktop/mobile map. Cookie authentication, saved preferences/places and authorized infrastructure edits use PostgreSQL/PostGIS. Private reports/evidence, transactional review and source-specific restrictions now drive durable live updates and confirmed rerouting. Routes retire on known changes, lost currentness or expiry. Optional private inference jobs and annotation review are implemented, but no approved dataset/evaluated hazard weights exist; image analysis stays disabled. All campus examples are fictional demonstration data, not a map or accessibility survey of Woxsen University.

## Start here

- [Project status](docs/PROJECT_STATUS.md) — implemented scope, evidence, and next authorized step.
- [Final engineering audit](docs/FINAL_ENGINEERING_AUDIT.md) — all 20 success criteria, six repaired findings, executed checks and remaining public-release limits.
- [Development setup](docs/DEVELOPMENT.md), [Phase 1 evidence](docs/PHASE1_TEST_EVIDENCE.md), [Phase 2 evidence](docs/PHASE2_TEST_EVIDENCE.md) [Phase 3 evidence](docs/PHASE3_TEST_EVIDENCE.md) [Phase 4 evidence](docs/PHASE4_TEST_EVIDENCE.md) [Phase 5 evidence](docs/PHASE5_TEST_EVIDENCE.md) and [Phase 6 evidence](docs/PHASE6_TEST_EVIDENCE.md).
- [Original project brief](docs/PROJECT_BRIEF.md) — preserved user requirements and phase boundaries.
- [Architecture](docs/ARCHITECTURE.md) and [decision records](docs/adr/README.md).
- [Database schema](docs/DATABASE_SCHEMA.md), [API contract](docs/API_CONTRACT.md), and [routing design](docs/ROUTING_DESIGN.md).
- [Security](docs/SECURITY.md), [reporting and live updates](docs/REPORTING_AND_EVENTS.md), [AI strategy](docs/AI_STRATEGY.md), and [frontend design](docs/FRONTEND_DESIGN.md).
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md), [testing](docs/TESTING.md), [risks and assumptions](docs/RISK_REGISTER.md), and [deployment plan](docs/DEPLOYMENT.md).
- [Model handoff](docs/MODEL_SWITCH_GUIDE.md).

## Repository structure

```text
frontend/src/       React pages, brand assets, live map, generated API client and tests
backend/app/        FastAPI, models, schemas, services and real-DB tests
backend/alembic/    Versioned PostgreSQL/PostGIS migrations and integrity triggers
ml/                Optional datasets, training, inference, evaluation boundaries
docs/              Architecture, contracts, decisions, examples, evidence
scripts/           Install, start, test, smoke and restart-persistence checks
.github/workflows/ Commit-pinned CI for application and release validation
deploy/            Pinned production API/UI builds and HTTPS proxy configuration
```

## Development quick start

From the repository root, with Python 3.12, Node 24 and Docker/Compose:

```sh
bash scripts/install.sh
bash scripts/start.sh
bash scripts/test.sh
bash scripts/test_frontend.sh
```

Installation creates private ignored local configuration, installs the Python hash lock and npm lock, starts persistent PostGIS, migrates and seeds only an empty fictional campus. Startup runs the API and Vite with real functional checks. Backend and browser tests each migrate isolated temporary PostGIS databases and preserve development data. See [development instructions](docs/DEVELOPMENT.md) for browser prerequisites, admin creation, stop and persistence checks.

There are no default administrator credentials. Use the secure interactive `create-admin` command. `.env.example` contains no secret values; never commit the populated `.env`. The pinned database image uses amd64 emulation on Apple Silicon. The backend has no fake route/report/ML success handlers.

## Release preparation

The release candidate runs the compiled UI and API through same-origin HTTPS in a separate Compose project, with non-root/read-only runtime containers and explicit migrations. Coordinated backups include PostgreSQL plus private evidence/model storage; restore refuses populated targets. See the [release runbook](docs/RELEASE_RUNBOOK.md) and [synthetic demonstration](docs/DEMO_SCRIPT.md).

```sh
bash scripts/test_release.sh
```

This verifies the local HTTPS candidate, production browser flow, real private-image backup/restore, retained restart and a clean source rebuild. It creates isolated local projects and retains their volumes for inspection. Public deployment, hosted CI, macOS execution and fresh cloud restoration require separate verification. Anonymous rate limits currently aggregate behind the proxy; public-capacity/proxy admission remains a release gate.

[CI](.github/workflows/ci.yml) uses reviewed action commit pins and the actual frozen install/test scripts. No publishing or automatic deployment job is included. Files remain locally saved and uncommitted; no push or deployment occurred. Cloud setup is a saved draft, with publication separate from current-instance validation.

The approved phased development/audit schedule is complete, with trained ML and public operational readiness explicitly limited. There is no automatic next phase. Follow-up scope and manual model/effort guidance are in [project status](docs/PROJECT_STATUS.md) and the [handoff guide](docs/MODEL_SWITCH_GUIDE.md).

Optional CPU tooling: [ML resource audit](docs/ML_RESOURCE_AUDIT.md) and [ML setup/training commands](ml/README.md). Synthetic pipeline tests and review doubles do not establish hazard accuracy.
