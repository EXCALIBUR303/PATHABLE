# Optional CPU image analysis

Phase 5 implements training/evaluation tools, safe tensor assets, protected durable inference jobs and human annotation review. **No licensed training dataset or evaluated hazard weights exist; product inference is disabled.** Read the [resource audit](../docs/ML_RESOURCE_AUDIT.md), [AI strategy](../docs/AI_STRATEGY.md) and [ADR-014](../docs/adr/014-phase5-optional-ml.md). Synthetic fixtures test execution only and cannot be registered as a product model.

## Install and test

From the checkout root, after the core install:

```sh
bash scripts/install_ml.sh
bash scripts/test_ml.sh
```

The separate ignored `.local/ml-venv` installs hash-locked CPU torch 2.14.1+cpu, NumPy 2.5.4, safetensors 0.8.0 and core dependencies. The lock currently targets Linux x86_64/Python 3.12. Mac optional ML is untested; do not install the Linux wheel there. No GPU or implicit model download is required. The helper preserves existing bindings and generates one local restricted-worker credential if absent, without enabling ML. No secrets are printed. Core install/start/tests work without the optional tensor environment.

## Supply real data before training

The [empty manifest template](../docs/examples/ml-dataset-template.json) deliberately fails rights/data gates. Each record needs `id`, controlled relative `file`, SHA-256, one declared `class_name`, `group_id` and `split` (train, validation or test). Review license/source/privacy first. Split by campus/scene/capture session; groups must not cross splits. Exact duplicates and near-identical cross-split perceptual hashes are rejected. All declared classes need observations in every split. The audit caps 10,000 records and 10 MiB/20M-pixel JPEG/PNG images. These minimum checks do not establish representative class balance or real-campus generalization.

With a rights-reviewed manifest and external images, run from the root:

```sh
export PYTHONPATH="$PWD/backend:$PWD"
.local/ml-venv/bin/python -m ml.pathable_ml.pipeline audit --manifest ml/datasets/manifest.json --images ml/datasets/raw
.local/ml-venv/bin/python -m ml.pathable_ml.pipeline train --manifest ml/datasets/manifest.json --images ml/datasets/raw --output ml/artifacts/evaluated --epochs 10 --seed 1729 --code-revision YOUR_REVIEWED_SOURCE_REVISION
.local/ml-venv/bin/python -m ml.pathable_ml.pipeline evaluate --manifest ml/datasets/manifest.json --images ml/datasets/raw --output ml/artifacts/evaluated --limitations "Document scene coverage, class support, errors and deployment limits"
```

Training uses a fixed 14,501-parameter five-class CPU CNN (parameter count varies with vocabulary), RGB 128px preprocessing, deterministic one-thread execution, Adam and validation-only checkpoint selection. It trains from scratch and makes image-level observations, with no boxes. Dataset suitability and architecture quality remain unresolved until real annotations/evaluation exist. Test images do not tune weights/thresholds. Evaluation is recorded once per artifact directory, with real confusion matrix, per-class precision/recall/F1/support, abstention counts, hashes, split counts and limitations. Scores are uncalibrated softmax outputs, never safety probabilities. No detection metrics are invented.

## Register and operate a real evaluated model

An operator must review actual evaluation/license/provenance before registration. Safe tensor state dictionaries only; no pickle or uploaded executable model code. From `backend/`:

```sh
../.venv/bin/python -m app.cli register-model --bundle ../ml/artifacts/evaluated --activate
```

Registration checks the bundle, rejects synthetic fixtures, runs the fixed tensor loader under resource/time bounds and copies immutable private assets into `.local/ml-models`. Model identity, dataset/weights/manifest/evaluation hashes and preprocessing are pinned. Registration alone does not enable the runtime. Set `ML_ENABLED=true` only after review and restart the owned API. Start the optional worker manually from `backend/`:

```sh
../.venv/bin/python -m app.services.ml_worker
# Single bounded iteration, useful for an empty queue smoke:
../.venv/bin/python -m app.services.ml_worker --once
```

The core worker coordinator uses its separate DB credential; tensor execution uses `.local/ml-venv/bin/python` and a sanitized environment. The worker may read models/evidence/jobs, update jobs and insert proposed predictions; it cannot edit graph state/restrictions, model metadata, evidence or prediction reviews. Short SKIP LOCKED leases last 120 seconds, attempts cap at three, timeout retries back off, and an expired token cannot publish. A shared advisory lock serializes evidence deletion with final publication without granting evidence UPDATE. CPU child limits are 4 GiB address space, 15 CPU seconds and 30 wall seconds; this is resource isolation, not a general malware sandbox. No long DB connection is held during compute.

API submission needs owner/admin access to a ready normalized image, CSRF/Origin and UUID Idempotency-Key. Jobs pin evidence/model hashes and are unique per evidence/model. The queue caps 100 pending/running jobs and submissions at 20/hour per user. Missing assets return typed 503; failure states remain separate from no observations. Annotated predictions retain model/source identity and optional abstention. Admin accept/reject uses expected_version/reason/idempotency and appends audit only. **Only a separate report verification transaction changes restrictions/routes.**

Large datasets/weights stay outside Git. Keep private assets, uploads and DB references together in release backups; model/evidence restore is not verified. An idle worker is not a monitored production service. Whole-system release/security/accessibility checks remain later phases.
