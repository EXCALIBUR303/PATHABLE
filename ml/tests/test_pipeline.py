"""Synthetic fixtures exercise CPU execution only, not hazard performance."""

import json
import random

import pytest
from app.ml_contracts import AssetError, bundle, digest
from PIL import Image

from ml.pathable_ml.dataset import audit
from ml.pathable_ml.metrics import classification
from ml.pathable_ml.model import classify
from ml.pathable_ml.pipeline import evaluate, train


@pytest.fixture
def data(tmp_path):
    root = tmp_path / "images"
    root.mkdir()
    rows = []
    for index in range(6):
        generator = random.Random(index)
        path = root / f"{index}.png"
        Image.frombytes(
            "RGB", (32, 32), bytes(generator.randrange(256) for _ in range(32 * 32 * 3))
        ).save(path)
        rows.append(
            {
                "id": str(index),
                "file": path.name,
                "sha256": digest(path),
                "class_name": ["stairs", "pathway_obstruction"][index % 2],
                "group_id": f"fixture-scene-{index}",
                "split": ["train", "validation", "test"][index // 2],
            }
        )
    manifest = {
        "schema_version": 1,
        "license": "TEST FIXTURE ONLY",
        "source": "synthetic seeded pixels",
        "privacy_reviewed": True,
        "approved_for_training": True,
        "synthetic_fixture": True,
        "classes": ["stairs", "pathway_obstruction"],
        "records": rows,
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(manifest))
    return path, root, manifest


def update(path, manifest):
    path.write_text(json.dumps(manifest))


def test_synthetic_data_cannot_be_used_as_product_training(data):
    with pytest.raises(AssetError, match="TEST_FIXTURE"):
        audit(data[0], data[1])


def test_valid_fixture_has_disjoint_group_class_counts(data):
    _, counts = audit(data[0], data[1], allow_fixture=True)
    assert counts == {
        split: {"stairs": 1, "pathway_obstruction": 1} for split in ["train", "validation", "test"]
    }


@pytest.mark.parametrize("field", ["privacy_reviewed", "approved_for_training"])
def test_unreviewed_rights_or_privacy_rejected(data, field):
    path, root, manifest = data
    manifest[field] = False
    update(path, manifest)
    with pytest.raises(AssetError, match="RIGHTS"):
        audit(path, root, allow_fixture=True)


def test_group_leakage_rejected(data):
    path, root, manifest = data
    manifest["records"][2]["group_id"] = manifest["records"][0]["group_id"]
    update(path, manifest)
    with pytest.raises(AssetError, match="GROUP_SPLIT"):
        audit(path, root, allow_fixture=True)


def test_changed_hash_and_traversal_rejected(data):
    path, root, manifest = data
    manifest["records"][0]["sha256"] = "0" * 64
    update(path, manifest)
    with pytest.raises(AssetError, match="HASH"):
        audit(path, root, allow_fixture=True)
    manifest["records"][0]["file"] = "../dataset.json"
    update(path, manifest)
    with pytest.raises(AssetError, match="PATH"):
        audit(path, root, allow_fixture=True)


def test_perceptual_copy_with_different_encoding_rejected(data):
    path, root, manifest = data
    with Image.open(root / "0.png") as image:
        image.save(root / "copy.png", compress_level=0)
    row = manifest["records"][2]
    row["file"] = "copy.png"
    row["sha256"] = digest(root / "copy.png")
    update(path, manifest)
    with pytest.raises(AssetError, match="PERCEPTUAL_SPLIT"):
        audit(path, root, allow_fixture=True)


def test_metric_counts_and_empty_denominators_are_explicit():
    value = classification(
        ["stairs", "pathway_obstruction"],
        ["stairs", "stairs", "pathway_obstruction"],
        ["stairs", "stairs", "stairs"],
    )
    assert value["confusion_matrix"] == [[2, 0], [1, 0]] and value["accuracy"] == 2 / 3
    assert value["per_class"][0]["precision"] == 2 / 3
    assert value["per_class"][1]["precision"] is None and value["per_class"][1]["recall"] == 0
    with pytest.raises(ValueError):
        classification(["stairs"], [], [])


def test_actual_cpu_training_is_deterministic_evaluation_and_safe_inference_work(data, tmp_path):
    path, root, _ = data
    first = tmp_path / "first"
    second = tmp_path / "second"
    left = train(
        path, root, first, epochs=1, code_revision="EXPLICIT SYNTHETIC FIXTURE", allow_fixture=True
    )
    right = train(
        path, root, second, epochs=1, code_revision="EXPLICIT SYNTHETIC FIXTURE", allow_fixture=True
    )
    assert left["weights_sha256"] == right["weights_sha256"]
    metrics = evaluate(
        path,
        root,
        first,
        limitations="Synthetic execution fixture, no hazard accuracy claim",
        allow_fixture=True,
    )
    assert metrics["sample_count"] == 2 and metrics["synthetic_fixture"] is True
    assert sum(map(sum, metrics["confusion_matrix"])) == 2
    manifest, _, _ = bundle(first, allow_fixture=True)
    result = classify(first, root / "4.png", allow_fixture=True)
    assert len(result["scores"]) == 2 and abs(sum(x["score"] for x in result["scores"]) - 1) < 1e-6
    assert isinstance(result["abstained"], bool)
    with pytest.raises(AssetError, match="TEST_FIXTURE"):
        bundle(first)
    with pytest.raises(AssetError, match="ALREADY_RECORDED"):
        evaluate(path, root, first, limitations="Fixture", allow_fixture=True)
    (first / "weights.safetensors").write_bytes(b"changed")
    with pytest.raises(AssetError, match="CHECKSUM"):
        bundle(first, allow_fixture=True)


def test_pickle_paths_and_unknown_model_architecture_rejected(data, tmp_path):
    path, root, _ = data
    destination = tmp_path / "bundle"
    train(path, root, destination, epochs=1, code_revision="fixture", allow_fixture=True)
    evaluate(path, root, destination, limitations="test only", allow_fixture=True)
    manifest = json.loads((destination / "manifest.json").read_text())
    manifest["architecture"] = "arbitrary-code"
    (destination / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(AssetError, match="INCOMPATIBLE"):
        bundle(destination, allow_fixture=True)
    manifest["architecture"] = "pathable-small-cnn-v1"
    manifest["weights_file"] = "weights.pkl"
    (destination / "weights.pkl").write_bytes(b"not executable")
    (destination / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(AssetError, match="CHECKSUM"):
        bundle(destination, allow_fixture=True)
