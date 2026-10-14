# Release candidate runbook

This prepares a single-host HTTPS release candidate. Local validation uses fictional `synthetic_demo` data and loopback ports. Public DNS/TLS provisioning, remote deployment and Git/environment publication require separate authorization. Image analysis remains disabled.

## Prerequisites and build

Python 3.12, Node 24, Docker Engine and Compose 2.17+ with BuildKit additional contexts are required. Reserve at least 8 GiB free for build layers; use a generous disk budget for repeated candidates. This release targets Linux amd64. Apple Silicon needs Docker amd64 emulation for every pinned image; macOS execution has not been verified. Native development instructions remain in [DEVELOPMENT.md](DEVELOPMENT.md).

From the repository root:

```sh
bash scripts/install.sh
bash scripts/prepare_release_artifacts.sh
.venv/bin/python scripts/configure_release.py --local-test
.venv/bin/python scripts/release.py build
.venv/bin/python scripts/release.py init --synthetic
.venv/bin/python scripts/release.py start
.venv/bin/python scripts/smoke_release.py
.venv/bin/python scripts/smoke_release_browser.py
```

The fixture generator creates a new private `.local/release/` directory, strong local credentials and a two-day localhost certificate. It refuses an existing directory. It does not modify development `.env` or its database volume. Never use that certificate as a public deployment certificate. Python explicitly trusts the fixture certificate while checking hostname/validity; the browser trusts only its public-key pin. Package downloads continue to require TLS, hash and npm integrity verification. Container builds themselves run with networking disabled.

For an operator-managed candidate, copy [.env.release.example](../.env.release.example) to a private mode-0600 file, configure unique release project/role names and strong credentials, supply `server.crt` (full chain) and `server.key` in the TLS directory, and set the exact HTTPS origin. Private directories must be separate and readable/writable by the configured non-root UID/GID; private keys remain mode 0600. Leave `RELEASE_CA_FILE` empty for public system roots or point it at an explicit private CA. Use `--env /absolute/private/config.env` with every command. Keep the loopback bind until deployment is explicitly authorized.

`init` runs controlled migrations/grants. `--synthetic` is explicit and seeds only an empty fictional campus; ordinary `init` does not invent campus infrastructure. API replicas never migrate themselves. The runtime API receives no owner credential. `ops` commands receive the owner binding only for their short-lived operation. There are no default administrator accounts:

```sh
.venv/bin/python scripts/release.py create-admin --email admin@example.com --name 'Campus administrator'
```

This command requires a terminal and securely prompts for the password twice. Never put it on the command line.

## Operation and upgrades

```sh
.venv/bin/python scripts/release.py status
.venv/bin/python scripts/smoke_release.py
.venv/bin/python scripts/release.py maintenance
.venv/bin/python scripts/release.py stop
```

`stop` stops API/web while retaining DB/private storage; `stop --all` also stops the DB process and retains its volume. Reuse `start` to resume. Health checks verify API readiness and Nginx configuration; the HTTP smoke additionally verifies TLS, production headers/host cookie, graph/routes and actual unbuffered SSE. Monitor health failures, HTTP 5xx/429 rates, DB connections/latency/disk, private storage growth and backup age. Generic API error responses include a request ID. Nginx/API access logging is disabled to avoid collecting navigation/evidence request histories by default. Configure reviewed observability and retention before public operation.

Schedule `release.py --env ... maintenance` hourly from the operator host, serialize it through this helper and alert on nonzero exit. It prunes only expired replay/leases/idempotency and interrupted/orphan uploads, preserving ready evidence. The helper uses a per-project operator lock, so maintenance does not overlap backup/restore. Do not run bypassing manual writers during a coordinated backup. A future enabled ML worker must be explicitly included in the quiescence workflow; current release configuration keeps ML disabled.

For an upgrade: record candidate image IDs and current migration revision, take/verify a coordinated backup, stop application services, build the reviewed candidate, run `init` once, start services and execute HTTP/browser/demo checks. Preserve the prior image and snapshot. Rolling back code against an incompatible schema is unsafe: restore the prior snapshot into a fresh project and validate it before switching traffic. No destructive downgrade, volume deletion or automatic rollback is provided.

## Coordinated backup and empty-target restore

```sh
.venv/bin/python scripts/backup_release.py backup --output /absolute/private/backup-directory
```

The new output directory must be outside live storage. API/web writers stop; a custom-format PostgreSQL dump and private uploads/model files are copied, and a checksum manifest is written last. Previously running application services resume even if backup fails. An incomplete snapshot has no valid manifest and must not be used. The backup contains personal data, password/session hashes and images: keep it private, encrypt it for off-host storage, define retention and routinely test restoration. TLS/operator credentials are intentionally excluded and need separate secure recovery.

Restore into a separately configured release project with stopped services, empty private directories and a pristine application DB:

```sh
.venv/bin/python scripts/backup_release.py --env /absolute/private/new-target.env restore --source /absolute/private/backup-directory
.venv/bin/python scripts/release.py --env /absolute/private/new-target.env start
.venv/bin/python scripts/smoke_release.py --env /absolute/private/new-target.env
```

The target DB is created from template0 if absent; existing schemas or application data are refused. Restore validates complete manifest metadata (including revision, timestamp and source identity), file membership, size/hash and regular-file paths before contacting the target. Run recovery as the configured runtime UID/GID or as a root operator. Staged uploads/models receive the configured runtime ownership before transactional `pg_restore`; this keeps mode-0600 evidence readable after root-operated recovery. An unprivileged mismatched identity is rejected before DB import. Restore then applies this target's current role credentials/grants. It never cleans or overwrites a populated target. Services remain stopped after restore for operator review. If a filesystem/grant/upgrade check fails after the DB import, keep the target stopped and investigate; do not resume a partially validated target. Backups must come from trusted operators: checksums detect corruption but do not authenticate SQL or model content.

```sh
.venv/bin/python scripts/verify_release_restore.py
bash scripts/test_release.sh
```

The first command exercises real HTTPS account/preferences/saved-place/report/private-image persistence through backup, fresh restore and retained restart, with an explicitly inert synthetic model-storage probe. The wrapper also checks corruption/path rejection and builds a clean nonignored source export with no-cache offline images. It reclaims only newly generated build-cache IDs and copied dependency caches, preserving earlier cache, images and data. It creates distinct local projects/private directories and retains their volumes for inspection; it stops their services afterward. It never resets the development DB. A source export is not a verified remote Git checkout: this repository currently has an unborn branch, and no push/hosted CI run is authorized.

## Release limits

The configured API ignores forwarded client IP headers. Anonymous rate limits aggregate behind Nginx; trusted proxy admission and representative capacity need a separate reviewed implementation before public use. CSP currently allows only self-hosted resources, with inline styles needed by Leaflet/React. Optional external tiles are not configured. Package advisory checks are distinct from OS/container scanning. Public certificate issuance/renewal, host hardening, encrypted off-host recovery, monitored capacity and manual assistive-technology review remain operator/audit gates. See [security](SECURITY.md), [resource limitations](ML_RESOURCE_AUDIT.md) and [Phase 7 evidence](PHASE7_TEST_EVIDENCE.md).
