# Deployment preparation

The release candidate uses pinned, offline-built API/UI images and a separate Compose project with same-origin HTTPS. API/web run as non-root users with read-only roots and resource/process bounds; private evidence and TLS keys are protected host mounts. The release DB has no host port. Image analysis remains disabled. See [release operations](RELEASE_RUNBOOK.md), [ADR-015](adr/015-phase7-release.md) and [Phase 7 evidence](PHASE7_TEST_EVIDENCE.md).

## Development and candidate separation

`bash scripts/install.sh` / `bash scripts/start.sh` retain native Python/Node development and its named PostGIS volume. `compose.release.yml` / `scripts/release.py` use separate projects/private configuration. Never substitute the development project name or delete volumes to recover a failure. Do not print resolved Compose configuration, which contains credentials.

The cloud host has Python 3.12.14, Node 24.19.0, npm 11.9.0, Docker 28.4.0 and Compose 2.40.3. Release images target Linux amd64. Apple Silicon needs emulation; macOS candidate execution is unverified. Run the existing isolated checkout without creating a Git worktree unless requested. Have at least 8 GiB free before building; temporary build layers need considerably more space than the reported final image sizes.

## Reproducible candidate

```sh
bash scripts/prepare_release_artifacts.sh
.venv/bin/python scripts/configure_release.py --local-test
.venv/bin/python scripts/release.py build
.venv/bin/python scripts/release.py init --synthetic
.venv/bin/python scripts/release.py start
.venv/bin/python scripts/smoke_release_browser.py
```

The generator creates only a new localhost fixture with private random credentials and a two-day certificate. Existing directories are refused. Operator configuration and public/private CA handling are in [.env.release.example](../.env.release.example) and the runbook. Python hash/npm integrity and download TLS checks remain enabled. Named verified BuildKit contexts make Docker builds independent of build-network DNS. `build --discard-build-cache` optionally reclaims only cache IDs newly created during that build, retaining previous cache, images and data; CI/clean-export checks use it.

The runtime API receives only its restricted DB credential. Explicit operator containers receive the owner password. Migrations/grants run once through `init`, apart from startup. Synthetic seeding is opt-in. PostGIS initializes a bootstrap DB separately from the application DB; TCP health waits past the temporary initialization socket server.

## CI and validation

[CI](../.github/workflows/ci.yml) pins official checkout/setup/upload action commits. It installs frozen core/optional CPU dependencies and the matching Playwright browser, runs the backend/ML/frontend wrappers, then `scripts/test_release.sh`. The release wrapper exercises strict HTTPS, production browser routes/auth, real DB/private-file restoration and a no-cache clean source export. Test projects are isolated and retained for inspection; no real user data is put in failure artifacts. No publication/deployment job is configured.

Local actionlint passed. Hosted CI remains unrun because the branch is unborn and no push is authorized. The current cloud proxy blocked the bundled Chromium download at `cdn.playwright.dev`; installed system Chromium runs local checks. That exact domain was added to the saved draft, preserving package-manager presets. Saving does not change the current runtime network policy; no successful bundled-browser download is claimed.

## Operations and recovery

Schedule serialized `release.py --env ... maintenance` hourly and alert on failure. It removes only expired replay/leases/idempotency and interrupted/orphan uploads, preserving ready evidence. Monitor health/5xx/429, DB connections/disk/latency, private storage growth and backup age. API/web access logging is off by default; configure reviewed observability and retention before public operation.

Coordinated backup stops writers and captures PostgreSQL plus private evidence/model storage with checksums. Restore requires stopped services, empty private directories and a pristine application DB, creates a missing DB from template0, imports transactionally, then applies current role credentials/grants. Existing data is never cleaned/overwritten. Only trusted operator backups may be restored; checksums are not signatures. TLS/config recovery and encrypted off-host retention are separate. The runbook supplies tested commands, upgrade/rollback steps and the [synthetic demo](DEMO_SCRIPT.md).

## Publication and remaining gates

Saved cloud installation/start instructions are separate from execution and publication. Review/save in environment settings, then publish when ready. Processes must restart after restoration. New-task restoration, volumes on another machine and a remote Git clone remain unverified; a local source export/restored candidate is narrower evidence.

Before public deployment, resolve trusted client-IP/proxy admission (anonymous quotas aggregate at Nginx), provision/renew real TLS/DNS, audit host/container OS, configure encrypted off-host recovery and monitored capacity, and complete manual assistive-technology review. The campus is fictional; approved evaluated hazard weights remain absent. Local candidate validation does not establish public navigation readiness.
