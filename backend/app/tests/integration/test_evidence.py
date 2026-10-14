"""Private evidence is decoded by the actual resource-limited Pillow subprocess."""

import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.main import app
from app.models.reporting import ReportEvidence
from app.services import evidence
from app.tests.conftest import login
from app.tests.integration.test_reporting import review, submit


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "upload_root", tmp_path / "private-evidence")


def image_bytes(format="PNG", exif=False):
    image = Image.new("RGB", (32, 24), "teal")
    output = io.BytesIO()
    metadata = Image.Exif()
    if exif:
        metadata[270] = "PRIVATE LOCATION NOTE"
    image.save(output, format=format, **({"exif": metadata} if exif else {}))
    return output.getvalue()


def upload(client, headers, row, data=None, mime="image/png", name="concern.png"):
    return client.post(
        f"/api/v1/reports/{row['id']}/evidence",
        headers=headers,
        data={"expected_version": str(row["row_version"])},
        files={"file": (name, image_bytes() if data is None else data, mime)},
    )


@pytest.mark.parametrize("stage", ["reservation", "publication", "deletion"])
def test_account_revoked_during_evidence_operation(client, user, monkeypatch, stage):
    from app.models.entities import User

    account, h = user
    report = submit(client, h)

    def revoke():
        with Session(engine()) as db, db.begin():
            db.get(User, uuid.UUID(account["id"])).active = False

    if stage == "deletion":
        item = upload(client, h, report).json()
        report = client.get(f"/api/v1/reports/{report['id']}").json()
        original = evidence.delete_evidence

        def revoked_delete(*args, **kwargs):
            revoke()
            return original(*args, **kwargs)

        monkeypatch.setattr(evidence, "delete_evidence", revoked_delete)
        response = client.request(
            "DELETE",
            f"/api/v1/reports/{report['id']}/evidence/{item['id']}",
            headers=h,
            json={"expected_version": report["row_version"]},
        )
    else:
        original = evidence.reserve if stage == "reservation" else evidence.subprocess.run

        def revoked_operation(*args, **kwargs):
            if stage == "reservation":
                revoke()
            value = original(*args, **kwargs)
            if stage == "publication":
                revoke()
            return value

        if stage == "reservation":
            monkeypatch.setattr(evidence, "reserve", revoked_operation)
        else:
            monkeypatch.setattr(evidence.subprocess, "run", revoked_operation)
        response = upload(client, h, report)
    assert response.status_code == 401
    with Session(engine()) as db:
        rows = list(db.scalars(select(ReportEvidence)))
        if stage == "reservation":
            assert rows == []
        else:
            assert len(rows) == 1
            assert rows[0].status == ("ready" if stage == "deletion" else "rejected")
            assert evidence.content_path(rows[0].storage_key).exists() == (stage == "deletion")
    assert not list(get_settings().private_upload_root.glob("*.input"))
    assert not list(get_settings().private_upload_root.glob("*.normalized"))


@pytest.mark.parametrize(
    "format,mime,name", [("PNG", "image/png", "concern.png"), ("JPEG", "image/jpeg", "concern.jpg")]
)
def test_normalized_private_image_and_metadata_removal(client, user, format, mime, name):
    _, headers = user
    row = submit(client, headers)
    source = image_bytes(format, exif=True)
    response = upload(client, headers, row, source, mime, name)
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["status"] == "ready" and item["width_px"] == 32 and item["height_px"] == 24
    assert len(item["sha256"]) == 64 and "storage_key" not in item and "uploader_id" not in item
    content = client.get(f"/api/v1/reports/{row['id']}/evidence/{item['id']}/content")
    assert content.status_code == 200 and "private" in content.headers["cache-control"]
    assert b"PRIVATE LOCATION NOTE" not in content.content
    with Image.open(io.BytesIO(content.content)) as image:
        assert not image.getexif() and image.format == format
    updated = client.get(f"/api/v1/reports/{row['id']}").json()
    assert updated["row_version"] == 3 and updated["evidence"] == [item]
    assert not list(get_settings().private_upload_root.glob("*.input"))
    assert not list(get_settings().private_upload_root.glob("*.normalized"))
    assert all(
        path.stat().st_mode & 0o777 == 0o600
        for path in get_settings().private_upload_root.iterdir()
    )


@pytest.mark.parametrize(
    "data,mime,name,status",
    [
        (b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', "image/svg+xml", "concern.svg", 415),
        (b"<svg></svg>", "image/png", "concern.png", 422),
        (b"not an image", "image/jpeg", "concern.jpg", 422),
        (b"PK\x03\x04archive", "image/png", "concern.png", 422),
        (b"", "image/png", "concern.png", 413),
        (image_bytes(), "image/jpeg", "concern.jpg", 422),
        (image_bytes()[:35], "image/png", "concern.png", 422),
        (image_bytes(), "image/png", "../../outside.png", 422),
        (image_bytes(), "image/png", "..\\outside.png", 422),
    ],
)
def test_invalid_images_and_path_components_never_become_ready(
    client, user, data, mime, name, status
):
    _, headers = user
    row = submit(client, headers)
    response = upload(client, headers, row, data, mime, name)
    assert response.status_code == status, response.text
    with Session(engine()) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReportEvidence)
                .where(ReportEvidence.status == "ready")
            )
            == 0
        )
    root = get_settings().private_upload_root
    assert not root.exists() or not list(root.iterdir())


def test_encoded_bytes_pixels_and_animation_are_bounded(client, user):
    _, headers = user
    row = submit(client, headers)
    response = upload(client, headers, row, b"x" * (evidence.MAX_BYTES + 1))
    assert response.status_code == 413, response.text
    row = client.get(f"/api/v1/reports/{row['id']}").json()
    huge = io.BytesIO()
    Image.new("1", (5000, 5000)).save(huge, format="PNG")
    assert upload(client, headers, row, huge.getvalue()).status_code == 422
    row = client.get(f"/api/v1/reports/{row['id']}").json()
    animated = io.BytesIO()
    first = Image.new("RGB", (16, 16), "red")
    first.save(
        animated, format="PNG", save_all=True, append_images=[Image.new("RGB", (16, 16), "blue")]
    )
    assert upload(client, headers, row, animated.getvalue()).status_code == 422
    with Session(engine()) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReportEvidence)
                .where(ReportEvidence.status == "ready")
            )
            == 0
        )


def test_auth_csrf_content_access_deletion_and_terminal_retention(client, user, admin):
    headers = login(client, "user@example.com")
    row = submit(client, headers)
    assert upload(client, {}, row).status_code == 403
    item = upload(client, headers, row).json()
    headers = login(client, "admin@example.com")
    content_url = f"/api/v1/reports/{row['id']}/evidence/{item['id']}/content"
    assert client.get(content_url).status_code == 200
    assert (
        upload(client, headers, client.get(f"/api/v1/reports/{row['id']}").json()).status_code
        == 404
    )
    updated = client.get(f"/api/v1/reports/{row['id']}").json()
    verified = review(client, headers, updated)
    assert verified.status_code == 200, verified.text
    headers = login(client, "user@example.com")
    assert upload(client, headers, verified.json()).status_code == 422
    deletion = client.request(
        "DELETE",
        f"/api/v1/reports/{row['id']}/evidence/{item['id']}",
        json={"expected_version": verified.json()["row_version"]},
        headers=headers,
    )
    assert deletion.status_code == 422
    assert client.get(content_url).status_code == 200
    client.cookies.clear()
    assert client.get(content_url).status_code == 401


def test_pending_owner_can_delete_and_stale_version_cannot(client, user):
    _, headers = user
    row = submit(client, headers)
    item = upload(client, headers, row).json()
    url = f"/api/v1/reports/{row['id']}/evidence/{item['id']}"
    assert (
        client.request("DELETE", url, json={"expected_version": 1}, headers=headers).status_code
        == 409
    )
    response = client.request("DELETE", url, json={"expected_version": 3}, headers=headers)
    assert response.status_code == 204, response.text
    assert client.get(url + "/content").status_code == 404
    assert not list(get_settings().private_upload_root.iterdir())


def test_three_slot_cap_and_user_storage_quota(client, user, monkeypatch):
    _, headers = user
    row = submit(client, headers)
    for _ in range(3):
        response = upload(client, headers, row)
        assert response.status_code == 201, response.text
        row = client.get(f"/api/v1/reports/{row['id']}").json()
    assert upload(client, headers, row).status_code == 409
    other = submit(client, headers)
    monkeypatch.setattr(get_settings(), "upload_user_quota_bytes", evidence.MAX_BYTES - 1)
    assert upload(client, headers, other).status_code == 413
    with Session(engine()) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReportEvidence)
                .where(ReportEvidence.status == "ready")
            )
            == 3
        )


def test_concurrent_uploads_with_same_version_cannot_overwrite_or_overfill(
    client, user, monkeypatch
):
    _, headers = user
    row = submit(client, headers)
    for _ in range(2):
        assert upload(client, headers, row).status_code == 201
        row = client.get(f"/api/v1/reports/{row['id']}").json()
    barrier = Barrier(2)
    original = evidence.reserve

    def synchronized(*args, **kwargs):
        barrier.wait(timeout=10)
        return original(*args, **kwargs)

    monkeypatch.setattr(evidence, "reserve", synchronized)

    def call(_):
        with TestClient(app) as other:
            other.cookies.update(client.cookies)
            return upload(other, headers, row)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(call, range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409], [
        response.text for response in responses
    ]
    with Session(engine()) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(ReportEvidence)
                .where(ReportEvidence.status.in_(["ready", "processing"]))
            )
            == 3
        )


def test_missing_file_is_unavailable_and_stored_path_traversal_is_rejected(client, user):
    from app.core.errors import Problem

    _, headers = user
    row = submit(client, headers)
    item = upload(client, headers, row).json()
    with Session(engine()) as db:
        key = db.get(ReportEvidence, uuid.UUID(item["id"])).storage_key
    evidence.content_path(key).unlink()
    response = client.get(f"/api/v1/reports/{row['id']}/evidence/{item['id']}/content")
    assert response.status_code == 503
    with pytest.raises(Problem):
        evidence.content_path("../../private.env")
