#!/usr/bin/env python3
"""Explicit synthetic prediction double, restricted to the disposable E2E database."""

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    from app.core.config import get_settings
    from app.models.ml import InferenceJob, ModelVersion, Prediction
    from app.models.reporting import ObstacleReport, ReportEvidence

    settings = get_settings()
    name = json.loads((ROOT / ".local/e2e-state.json").read_text())["database"]
    if not re.fullmatch(r"pathable_e2e_[0-9a-f]{12}", name) or name == settings.postgres_db:
        raise SystemExit("Refusing a non-disposable database")
    engine = create_engine(settings.database_url(owner=True, database=name), hide_parameters=True)
    with Session(engine) as db, db.begin():
        report = db.get(ObstacleReport, UUID(sys.argv[1]))
        image = db.get(ReportEvidence, UUID(sys.argv[2]))
        if not report or not image or image.report_id != report.id or image.status != "ready":
            raise SystemExit("Fixture requires owned ready test evidence")
        model = ModelVersion(
            name="EXPLICIT SYNTHETIC BROWSER FIXTURE",
            architecture="pathable-small-cnn-v1",
            weights_sha256="a" * 64,
            dataset_manifest_sha256="b" * 64,
            manifest_sha256=uuid4().hex * 2,
            bundle_key=uuid4().hex,
            code_revision="browser-test-double",
            license_summary="test-only synthetic fixture",
            preprocessing_json={
                "classes": ["stairs", "pathway_obstruction"],
                "score_threshold": 0.7,
                "margin_threshold": 0.15,
            },
            evaluation_json={"synthetic_fixture": True},
            evaluated_at=datetime.now(UTC),
            test_fixture=True,
        )
        db.add(model)
        db.flush()
        job = InferenceJob(
            report_id=report.id,
            evidence_id=image.id,
            requested_by=report.reporter_id,
            model_version_id=model.id,
            evidence_sha256=image.sha256,
            status="running",
            attempts=1,
            lease_token=uuid4(),
            leased_until=datetime.now(UTC) + timedelta(seconds=120),
        )
        db.add(job)
        db.flush()
        for label, score in (("stairs", 0.8), ("pathway_obstruction", 0.2)):
            db.add(
                Prediction(
                    job_id=job.id,
                    report_id=report.id,
                    evidence_id=image.id,
                    model_version_id=model.id,
                    class_name=label,
                    score=score,
                )
            )
        db.flush()
        job.status, job.latency_ms, job.abstained = "succeeded", 5, False
        job.lease_token = job.leased_until = None
    engine.dispose()
    print("Seeded explicit synthetic annotation test double; no product model enabled")


if __name__ == "__main__":
    main()
