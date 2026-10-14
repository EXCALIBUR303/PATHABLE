"""Approved immutable model bundles; unavailable ML never blocks manual workflows."""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select, text

from app.core.config import ROOT, get_settings
from app.ml_contracts import AssetError, bundle, digest
from app.models.ml import ModelVersion


def model_root(model):
    if not re.fullmatch("[0-9a-f]{32}", model.bundle_key):
        raise AssetError("INVALID_MODEL_REFERENCE")
    root = get_settings().private_ml_root.resolve()
    path = (root / model.bundle_key).resolve()
    if not path.is_relative_to(root):
        raise AssetError("INVALID_MODEL_REFERENCE")
    return path


def verify(model):
    path = model_root(model)
    if digest(path / "manifest.json", 128 * 1024) != model.manifest_sha256:
        raise AssetError("MODEL_MANIFEST_CHANGED")
    manifest, result, _ = bundle(path)
    if (
        manifest["weights_sha256"] != model.weights_sha256
        or manifest["dataset_manifest_sha256"] != model.dataset_manifest_sha256
    ):
        raise AssetError("MODEL_PROVENANCE_CHANGED")
    return manifest, result


def availability(db):
    settings = get_settings()
    if not settings.ml_enabled:
        return None, "DISABLED"
    model = db.scalar(select(ModelVersion).where(ModelVersion.enabled))
    if model is None:
        return None, "EVALUATED_MODEL_MISSING"
    if model.test_fixture:
        return None, "TEST_FIXTURE_NOT_PRODUCT_MODEL"
    if not settings.ml_python.is_file():
        return None, "ML_RUNTIME_MISSING"
    if settings.ml_worker_db_password is None:
        return None, "ML_WORKER_NOT_CONFIGURED"
    try:
        verify(model)
    except (AssetError, OSError, ValueError, TypeError, KeyError):
        return None, "MODEL_ASSETS_INVALID"
    return model, "READY"


def register(db, source, *, activate=False):
    """Explicit owner CLI only. Copy/validate before transactional registration."""
    settings = get_settings()
    manifest, result, weights = bundle(source)
    if not settings.ml_python.is_file():
        raise AssetError("ML_RUNTIME_MISSING")
    identity = uuid4()
    root = settings.private_ml_root
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = root / identity.hex
    destination.mkdir(mode=0o700)
    try:
        shutil.copyfile(weights, destination / "weights.safetensors")
        from app.ml_contracts import controlled_file

        shutil.copyfile(
            controlled_file(source, manifest["evaluation_file"]), destination / "evaluation.json"
        )
        manifest.update(weights_file="weights.safetensors", evaluation_file="evaluation.json")
        (destination / "manifest.json").write_text(
            json.dumps(manifest, indent=2, allow_nan=False) + "\n"
        )
        for path in destination.iterdir():
            path.chmod(0o400)
        bundle(destination)
        subprocess.run(
            [
                str(settings.ml_python),
                "-m",
                "app.services.ml_tensor_process",
                "--validate",
                str(destination),
            ],
            cwd=ROOT / "backend",
            env=child_environment(),
            timeout=30,
            check=True,
            capture_output=True,
        )
        if activate:
            db.execute(text("SELECT pg_advisory_xact_lock(5149051)"))
            for prior in db.scalars(
                select(ModelVersion).where(ModelVersion.enabled).with_for_update()
            ):
                prior.enabled = False
            db.flush()
        row = ModelVersion(
            id=identity,
            name=manifest["name"],
            architecture=manifest["architecture"],
            weights_sha256=manifest["weights_sha256"],
            dataset_manifest_sha256=manifest["dataset_manifest_sha256"],
            manifest_sha256=digest(destination / "manifest.json"),
            bundle_key=identity.hex,
            code_revision=manifest["code_revision"],
            license_summary=manifest["license"],
            preprocessing_json={
                "version": manifest["preprocessing"],
                "classes": manifest["classes"],
                "score_threshold": manifest["score_threshold"],
                "margin_threshold": manifest["margin_threshold"],
            },
            evaluation_json=result,
            evaluated_at=datetime.fromisoformat(result["evaluated_at"]),
            enabled=activate,
        )
        db.add(row)
        db.flush()
        return row
    except Exception:
        shutil.rmtree(destination)
        raise


def child_environment():
    # No inherited database/session/proxy credentials. No child Settings import.
    return {
        "PATH": os.defpath,
        "PYTHONPATH": str(ROOT) + os.pathsep + str(ROOT / "backend"),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
