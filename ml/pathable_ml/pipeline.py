"""Reproducible CPU training and held-out evaluation; no implicit downloads."""

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path

from ml.pathable_ml.contracts import (
    ARCHITECTURE,
    PREPROCESSING,
    AssetError,
    controlled_file,
    digest,
    read_json,
)
from ml.pathable_ml.dataset import audit
from ml.pathable_ml.metrics import classification


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def train(
    manifest_path,
    images,
    output,
    *,
    epochs=10,
    seed=1729,
    code_revision,
    allow_fixture=False,
):
    import torch
    from safetensors.torch import save_file

    from ml.pathable_ml.model import network, tensor

    if not 1 <= epochs <= 100 or not code_revision:
        raise AssetError("INVALID_TRAINING_CONFIGURATION")
    data, counts = audit(manifest_path, images, allow_fixture=allow_fixture)
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    model = network(len(data["classes"]))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_function = torch.nn.CrossEntropyLoss()
    rows = {
        split: [r for r in data["records"] if r["split"] == split]
        for split in ("train", "validation")
    }
    history, best = [], -1
    for epoch in range(epochs):
        model.train()
        random.shuffle(rows["train"])
        total = 0.0
        for row in rows["train"]:
            optimizer.zero_grad()
            score = model(tensor(controlled_file(images, row["file"])).unsqueeze(0))
            loss = loss_function(score, torch.tensor([data["classes"].index(row["class_name"])]))
            loss.backward()
            optimizer.step()
            total += loss.item()
        model.eval()
        correct = 0
        with torch.inference_mode():
            for row in rows["validation"]:
                index = (
                    model(tensor(controlled_file(images, row["file"])).unsqueeze(0))
                    .argmax(1)
                    .item()
                )
                correct += data["classes"][index] == row["class_name"]
        accuracy = correct / len(rows["validation"])
        history.append(
            {
                "epoch": epoch + 1,
                "training_loss": total / len(rows["train"]),
                "validation_accuracy": accuracy,
            }
        )
        if accuracy > best:
            best = accuracy
            save_file(model.state_dict(), str(destination / "weights.safetensors"))
    manifest = {
        "schema_version": 1,
        "name": "pathable-small-cnn-v1",
        "architecture": ARCHITECTURE,
        "preprocessing": PREPROCESSING,
        "classes": data["classes"],
        "weights_file": "weights.safetensors",
        "weights_sha256": digest(destination / "weights.safetensors"),
        "dataset_manifest_sha256": digest(manifest_path, 8 * 1024 * 1024),
        "evaluation_file": "evaluation.json",
        "evaluation_sha256": "0" * 64,
        "license": data["license"],
        "code_revision": code_revision,
        "synthetic_fixture": data["synthetic_fixture"],
        "score_threshold": 0.7,
        "margin_threshold": 0.15,
    }
    write(destination / "manifest.json", manifest)
    write(
        destination / "training.json",
        {
            "seed": seed,
            "epochs": epochs,
            "hardware": "CPU, one tensor thread",
            "torch_version": torch.__version__,
            "split_counts": counts,
            "history": history,
            "selection": "highest validation accuracy, earliest tie; test not used",
        },
    )
    return manifest


def evaluate(manifest_path, images, output, *, limitations, allow_fixture=False):
    import torch
    from safetensors.torch import load_file

    from ml.pathable_ml.model import network, tensor

    data, counts = audit(manifest_path, images, allow_fixture=allow_fixture)
    root = Path(output)
    manifest = read_json(root / "manifest.json")
    if (
        manifest["architecture"] != ARCHITECTURE
        or manifest["preprocessing"] != PREPROCESSING
        or manifest["classes"] != data["classes"]
        or manifest["dataset_manifest_sha256"] != digest(manifest_path, 8 * 1024 * 1024)
        or not limitations
        or manifest["synthetic_fixture"] != data["synthetic_fixture"]
    ):
        raise AssetError("EVALUATION_PROVENANCE_MISMATCH")
    if (root / "evaluation.json").exists():
        raise AssetError("HELD_OUT_EVALUATION_ALREADY_RECORDED")
    weights = controlled_file(root, manifest["weights_file"])
    if weights.suffix != ".safetensors" or digest(weights) != manifest["weights_sha256"]:
        raise AssetError("WEIGHTS_CHECKSUM_MISMATCH")
    torch.set_num_threads(1)
    model = network(len(data["classes"]))
    model.load_state_dict(load_file(str(weights), device="cpu"), strict=True)
    model.eval()
    expected, predicted = [], []
    abstained = 0
    with torch.inference_mode():
        for row in data["records"]:
            if row["split"] != "test":
                continue
            scores = torch.softmax(
                model(tensor(controlled_file(images, row["file"])).unsqueeze(0)), dim=1
            )[0].tolist()
            order = sorted(scores, reverse=True)
            abstained += (
                order[0] < manifest["score_threshold"]
                or order[0] - order[1] < manifest["margin_threshold"]
            )
            expected.append(row["class_name"])
            predicted.append(data["classes"][max(range(len(scores)), key=scores.__getitem__)])
    result = {
        **classification(data["classes"], expected, predicted),
        "classes": data["classes"],
        "split": "test",
        "dataset_manifest_sha256": manifest["dataset_manifest_sha256"],
        "weights_sha256": manifest["weights_sha256"],
        "synthetic_fixture": data["synthetic_fixture"],
        "evaluated_at": datetime.now(UTC).isoformat(),
        "split_counts": counts,
        "abstained_count": abstained,
        "score_threshold": manifest["score_threshold"],
        "margin_threshold": manifest["margin_threshold"],
        "limitations": limitations,
        "score_meaning": "uncalibrated softmax model scores; not route safety probabilities",
        "protocol": "single-label argmax classification; no localization metrics",
    }
    write(root / "evaluation.json", result)
    manifest["evaluation_sha256"] = digest(root / "evaluation.json")
    write(root / "manifest.json", manifest)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["audit", "train", "evaluate"])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--output")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--code-revision")
    parser.add_argument("--limitations")
    args = parser.parse_args()
    if args.action == "audit":
        result = audit(args.manifest, args.images)[1]
    elif args.action == "train":
        if not args.output or not args.code_revision:
            parser.error("train requires --output and --code-revision")
        result = train(
            args.manifest,
            args.images,
            args.output,
            epochs=args.epochs,
            seed=args.seed,
            code_revision=args.code_revision,
        )
    else:
        if not args.output or not args.limitations:
            parser.error("evaluate requires --output and --limitations")
        result = evaluate(args.manifest, args.images, args.output, limitations=args.limitations)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
