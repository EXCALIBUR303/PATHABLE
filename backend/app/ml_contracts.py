"""Small, strict asset contracts shared by training, registration and inference."""

import hashlib
import json
import re
from pathlib import Path

ARCHITECTURE = "pathable-small-cnn-v1"
PREPROCESSING = "rgb-resize128-scale01-v1"
LABELS = {
    "stairs",
    "pathway_obstruction",
    "damaged_pavement",
    "ramp_obstruction",
    "no_visible_target",
}
MAX_WEIGHTS = 25 * 1024 * 1024


class AssetError(ValueError):
    pass


def read_json(path, maximum=128 * 1024):
    path = Path(path)
    if path.stat().st_size > maximum:
        raise AssetError("ASSET_TOO_LARGE")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise AssetError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    try:
        return json.loads(
            path.read_text(),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(AssetError("NONFINITE_JSON")),
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise AssetError("INVALID_JSON") from error


def digest(path, maximum=MAX_WEIGHTS):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > maximum:
        raise AssetError("ASSET_MISSING_OR_TOO_LARGE")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            result.update(chunk)
    return result.hexdigest()


def controlled_file(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise AssetError("INVALID_ASSET_PATH")
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or path == root or not path.is_file():
        raise AssetError("INVALID_ASSET_PATH")
    return path


def vocabulary(values):
    if (
        not isinstance(values, list)
        or not 2 <= len(values) <= len(LABELS)
        or any(not isinstance(x, str) or x not in LABELS for x in values)
        or len(set(values)) != len(values)
    ):
        raise AssetError("INVALID_CLASS_VOCABULARY")
    return values


def bundle(root, *, allow_fixture=False):
    root = Path(root)
    manifest = read_json(root / "manifest.json")
    if set(manifest) != {
        "schema_version",
        "name",
        "architecture",
        "preprocessing",
        "classes",
        "weights_file",
        "weights_sha256",
        "dataset_manifest_sha256",
        "evaluation_file",
        "evaluation_sha256",
        "license",
        "code_revision",
        "synthetic_fixture",
        "score_threshold",
        "margin_threshold",
    }:
        raise AssetError("INVALID_MODEL_MANIFEST")
    if (
        manifest["schema_version"] != 1
        or manifest["architecture"] != ARCHITECTURE
        or manifest["preprocessing"] != PREPROCESSING
    ):
        raise AssetError("INCOMPATIBLE_MODEL")
    vocabulary(manifest["classes"])
    if manifest["synthetic_fixture"] is not False and not allow_fixture:
        raise AssetError("TEST_FIXTURE_NOT_PRODUCT_MODEL")
    if not isinstance(manifest["name"], str) or not 1 <= len(manifest["name"]) <= 100:
        raise AssetError("INVALID_MODEL_NAME")
    for key in ("weights_sha256", "dataset_manifest_sha256", "evaluation_sha256"):
        if not isinstance(manifest[key], str) or not re.fullmatch("[0-9a-f]{64}", manifest[key]):
            raise AssetError("INVALID_ASSET_HASH")
    if not manifest["license"] or not manifest["code_revision"]:
        raise AssetError("MISSING_PROVENANCE")
    for key in ("score_threshold", "margin_threshold"):
        value = manifest[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= 1:
            raise AssetError("INVALID_ABSTENTION_THRESHOLD")
    weights = controlled_file(root, manifest["weights_file"])
    if weights.suffix != ".safetensors" or digest(weights) != manifest["weights_sha256"]:
        raise AssetError("WEIGHTS_CHECKSUM_MISMATCH")
    evaluation = controlled_file(root, manifest["evaluation_file"])
    if digest(evaluation, 128 * 1024) != manifest["evaluation_sha256"]:
        raise AssetError("EVALUATION_CHECKSUM_MISMATCH")
    result = read_json(evaluation)
    if (
        result.get("dataset_manifest_sha256") != manifest["dataset_manifest_sha256"]
        or result.get("weights_sha256") != manifest["weights_sha256"]
        or result.get("split") != "test"
        or result.get("classes") != manifest["classes"]
        or result.get("synthetic_fixture") != manifest["synthetic_fixture"]
        or result.get("sample_count", 0) <= 0
        or not result.get("limitations")
    ):
        raise AssetError("INVALID_HELD_OUT_EVALUATION")
    return manifest, result, weights
