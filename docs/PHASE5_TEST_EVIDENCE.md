# Phase 5 — Optional ML integration evidence

Verified 2026-10-13 in `/workspace/PATHABLE`, saved locally and uncommitted on unborn `work`. User authorization ends at Phase 5. Scheduled GPT-6 Astra / Extra High; exact runtime model/effort is unverified. No commit, push, deployment or environment publication.

**Integration and the executable CPU pipeline are implemented; trained hazard inference is unavailable.** No licensed, scene-grouped hazard dataset or evaluated weights exist. See [resource audit](ML_RESOURCE_AUDIT.md) for missing resources and [ADR-014](adr/014-phase5-optional-ml.md) for the conditional classifier design. The resource-limited fallback allowed by the project brief is complete; this is not a claim of trained-model capability or hazard accuracy.

## Executed checks

| Command from repository root | Actual result |
| --- | --- |
| `bash scripts/test.sh` | Ruff/format passed; **320 backend tests passed**, 68.15s; one existing Starlette/httpx deprecation warning, no failures/skips/xfails |
| `bash scripts/test_ml.sh` | Scoped Ruff/format passed; **10 CPU pipeline tests passed**, 3.49s; no failures/skips |
| `bash scripts/test_frontend.sh` | Contract/type/lint/format/build passed; **41 Vitest tests in 10 files**, 5.52s; **19 real full-stack Playwright tests**, 1.5m, one worker, no retries/skips |

Backend counts are the earlier 303 plus 17 new ML tests. The ten separate CPU tests are not included in 320. Frontend adds three annotation/unavailable component tests and one full-stack boundary case to the earlier 38/18. Logs: `/tmp/pathable-phase5-backend-final.log`, `/tmp/pathable-phase5-ml-tests.log`, `/tmp/pathable-phase5-frontend-final.log`. Browser FORCE_COLOR/NO_COLOR and reduced-motion notices remain expected.

## What these checks prove

- Critical F passes through real DB/API and browser review: proposed and accepted predictions do not create/release restrictions or change graph revisions/events. Annotation acceptance appends an audit action with null graph version and leaves the report pending. Normal users cannot review; CSRF, owner scopes and role freshness are preserved.
- All successful stored predictions in these tests are **explicit synthetic compute doubles**, with persisted `test_fixture:true`, inactive model records and visible UI labels. Product activation rejects fixtures. The browser uses a helper restricted to its UUID-named disposable DB, not a fake success endpoint or a trained model.
- The actual restricted database worker coordinator claims and commits a synthetic result without graph/restriction/evidence/model/review privileges. Independent workers cannot claim one job twice. Expired tokens cannot publish, timeout retries cap at three, invalid/nonfinite scores roll back, and deleted evidence cannot receive late output. Concurrent opposing annotation reviews yield one 200 and one 409 with one audit record and no graph effects.
- CPU tests execute actual deterministic one-epoch training, held-out evaluation serialization and safe tensor inference on seeded synthetic pixels. Repeated weights match; hashes, group/exact/perceptual split leakage, rights flags, path traversal, architecture compatibility, pickle rejection, immutable evaluation and metric denominator cases are checked. **These fixture metrics are not product performance and are not reported as hazard precision/recall/F1.**
- The UI shows honest unavailable analysis while manual reporting works, labels model scores as uncalibrated and preserves stale annotation reasons/original versions. Private prediction/job queries are removed on login/logout. Existing reporting, uploads, analytics, live rerouting, offline recovery and account/profile race checks continue to pass.

The annotation screenshot `.local/screenshots/phase5-annotation-review.png` was inspected: accepted test annotation, explicit synthetic/model-score caveats, independent pathway verification controls and audit text “No graph change.” Whole-system accessibility remains Phase 6.

The existing report-to-client retirement browser measured 1577 ms in this run, under the connected two-second target for that one synthetic scenario. This is not a concurrent-load guarantee. No routing benchmark or retained-volume restart was repeated.

## Migration and asset boundaries

Head `0003_ml` adds model_versions, inference_jobs and predictions (25 total tables). Model/job/prediction provenance is immutable; reviews are final/CAS-controlled. Same-report evidence/job/model references and unique evidence/model jobs prevent mismatched or duplicate lineage. Classification returns no boxes. ML schema additions do not change routing semantics or advance graph revisions; the real foundation-to-head upgrade preserves an edited edge and the earlier reporting reset.

The optional CPU environment is separate from `.venv`; torch 2.14.1+cpu reports no compiled CUDA, NumPy 2.5.4 and safetensors 0.8.0 load successfully. Official wheel/hash verification remains enabled. The first frozen install identified a missing setuptools pin; the regenerated lock includes it with hashes. No verification bypass was used.

The restricted-role execution test exposed PostgreSQL FOR SHARE requiring evidence UPDATE privilege. A shared advisory content lock now serializes deletion/publication while retaining read-only evidence privileges, and the real worker test passes. The first new browser attempt selected an article in the admin table; it now uses the actual row. Final assertions were retained and no product test was disabled.

## Outstanding resources and release work

No actual hazard training/evaluation or successful product inference ran. Required resources: rights/privacy-reviewed image labels and scene-grouped splits covering the chosen ontology, measured held-out errors/generalization, reviewed safe weights and immutable evaluation/provenance. Registration rejects synthetic fixtures; `/ml/status` reports unavailable and inference returns ML_UNAVAILABLE. Manual navigation/reporting remains available.

The lock supports Linux x86_64/Python 3.12; macOS optional ML is unverified. No detection, localization, calibrated safety probability, trained accuracy, GPU capacity or production-readiness claim. Worker monitoring/scheduling, real asset backup/restore, full accessibility/security/capacity and fresh-task restoration remain future gates.

## Installation, startup and reusable configuration

`bash scripts/install.sh` exited 0 with hash-verified core dependencies, frozen npm install (378 packages), retained DB health, additive migrations/role grants and preserve-existing seed. `bash scripts/install_ml.sh` exited 0 on repeat, with both locks verified, pip check clean and the existing local worker binding preserved. Logs: `/tmp/pathable-phase5-install-core.log`, `/tmp/pathable-phase5-install-ml-final.log`.

Owned API/UI were stopped before refresh. `bash scripts/start.sh` exited 0 with current migration/seed/maintenance and actual API/routing/SSE/frontend/proxy checks; the new read-only ML smoke reports DISABLED. Log: `/tmp/pathable-phase5-start-final.log`. From backend, `../.venv/bin/python -m app.services.ml_worker --once` exited 0 with processed:false on the real empty development queue and restricted credential. No trained output was invented, no DB volume reset or shared DB restart.

Dependency package-manager network presets already include the actual PyTorch wheel hosts. Only repository install/start instructions need a draft update; unrelated repositories, network and secret requirements are preserved. Current-instance validation, saved configuration and publication remain distinct. Final read-only cleanup found zero disposable test/E2E/upgrade databases, zero temporary ML test roles, zero SSE leases and zero browser upload directories. Development model/job/prediction counts are all zero. Scoped backend/ML/helper Ruff and format, shell syntax, pip check, frontend formatting, Markdown links/whitespace/JSON and git diff checks pass. The explicit scan covers 244 nonignored files (important on an unborn branch); OpenAPI has 47 operations/43 paths.

Complete core-plus-optional install_script and Phase 5 start_skill are confirmed saved in the cloud draft (`status=saved`, `requires_publish=true`), and a readback matches both contents. Repository/network/secret settings were preserved. Review/save in environment settings, then publish to activate reuse; publication/fresh-task restore were not performed.
