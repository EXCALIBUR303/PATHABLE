"""Fixed CPU architecture and immutable preprocessing, no executable checkpoints."""

import numpy as np
import torch
from safetensors.torch import load_file
from torch import nn

from ml.pathable_ml.contracts import bundle
from ml.pathable_ml.dataset import open_image


def network(classes):
    return nn.Sequential(
        nn.Conv2d(3, 16, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(16, 32, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(32, 32, 3, padding=1),
        nn.ReLU(),
        nn.AdaptiveAvgPool2d(1),
        nn.Flatten(),
        nn.Linear(32, classes),
    )


def tensor(path):
    array = np.array(open_image(path).resize((128, 128)), dtype=np.float32) / 255.0
    return torch.from_numpy(array).permute(2, 0, 1).contiguous()


def load(root, *, allow_fixture=False):
    manifest, _, weights = bundle(root, allow_fixture=allow_fixture)
    torch.set_num_threads(1)
    model = network(len(manifest["classes"]))
    model.load_state_dict(load_file(str(weights), device="cpu"), strict=True)
    model.eval()
    return manifest, model


def classify(root, image_path, *, allow_fixture=False):
    manifest, model = load(root, allow_fixture=allow_fixture)
    with torch.inference_mode():
        scores = torch.softmax(model(tensor(image_path).unsqueeze(0)), dim=1)[0].tolist()
    order = sorted(scores, reverse=True)
    return {
        "scores": [
            {"class_name": label, "score": score}
            for label, score in zip(manifest["classes"], scores, strict=True)
        ],
        "abstained": order[0] < manifest["score_threshold"]
        or order[0] - order[1] < manifest["margin_threshold"],
    }
