"""Licensed single-label manifests with group/hash leakage checks."""

from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

from ml.pathable_ml.contracts import (
    AssetError,
    controlled_file,
    digest,
    read_json,
    vocabulary,
)


def open_image(path):
    if Path(path).stat().st_size > 10 * 1024 * 1024:
        raise AssetError("IMAGE_BYTES_EXCEEDED")
    with Image.open(path) as image:
        if (
            image.format not in {"JPEG", "PNG"}
            or getattr(image, "n_frames", 1) != 1
            or image.width * image.height > 20_000_000
        ):
            raise AssetError("INVALID_DATASET_IMAGE")
        image.verify()
    with Image.open(path) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")


def perceptual_hash(image):
    values = list(image.convert("L").resize((9, 8)).get_flattened_data())
    return sum(
        (values[row * 9 + col] > values[row * 9 + col + 1]) << (row * 8 + col)
        for row in range(8)
        for col in range(8)
    )


def audit(manifest_path, image_root, *, allow_fixture=False):
    data = read_json(manifest_path, 8 * 1024 * 1024)
    if (
        set(data)
        != {
            "schema_version",
            "license",
            "source",
            "privacy_reviewed",
            "approved_for_training",
            "synthetic_fixture",
            "classes",
            "records",
        }
        or data["schema_version"] != 1
    ):
        raise AssetError("INVALID_DATASET_MANIFEST")
    vocabulary(data["classes"])
    if (
        not data["license"]
        or not data["source"]
        or data["privacy_reviewed"] is not True
        or data["approved_for_training"] is not True
    ):
        raise AssetError("DATASET_RIGHTS_NOT_REVIEWED")
    if data["synthetic_fixture"] is not False and not allow_fixture:
        raise AssetError("TEST_FIXTURE_NOT_TRAINING_DATA")
    records = data["records"]
    if not isinstance(records, list) or not 6 <= len(records) <= 10000:
        raise AssetError("INVALID_DATASET_SIZE")
    ids, hashes, groups, near = set(), set(), {}, []
    counts = Counter()
    for row in records:
        if (
            set(row) != {"id", "file", "sha256", "class_name", "group_id", "split"}
            or row["split"] not in {"train", "validation", "test"}
            or row["class_name"] not in data["classes"]
        ):
            raise AssetError("INVALID_DATASET_RECORD")
        if (
            not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in ids
            or not isinstance(row["group_id"], str)
            or not row["group_id"]
        ):
            raise AssetError("INVALID_RECORD_ID")
        ids.add(row["id"])
        path = controlled_file(image_root, row["file"])
        if digest(path, 10 * 1024 * 1024) != row["sha256"] or row["sha256"] in hashes:
            raise AssetError("IMAGE_HASH_MISMATCH_OR_DUPLICATE")
        hashes.add(row["sha256"])
        if row["group_id"] in groups and groups[row["group_id"]] != row["split"]:
            raise AssetError("GROUP_SPLIT_LEAKAGE")
        groups[row["group_id"]] = row["split"]
        code = perceptual_hash(open_image(path))
        if any(split != row["split"] and (code ^ other).bit_count() <= 4 for other, split in near):
            raise AssetError("PERCEPTUAL_SPLIT_LEAKAGE")
        near.append((code, row["split"]))
        counts[(row["split"], row["class_name"])] += 1
    if any(
        counts[(split, label)] == 0
        for split in ("train", "validation", "test")
        for label in data["classes"]
    ):
        raise AssetError("CLASS_MISSING_FROM_SPLIT")
    return data, {
        split: {label: counts[(split, label)] for label in data["classes"]}
        for split in ("train", "validation", "test")
    }
