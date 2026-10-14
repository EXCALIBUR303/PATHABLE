# Phase 5 ML resource audit

Observed 2026-10-13 in `/workspace/PATHABLE`. No dataset manifests, annotated image collections, pretrained hazard weights or evaluated model bundles exist in `ml/` or the project runtime asset directories. Private user evidence and browser screenshots are not training data and were not repurposed. No approved external dataset/license/consent agreement was supplied.

The host has five visible CPUs, a four-CPU cgroup quota, 32 GiB memory limit and approximately 21.5 GiB free workspace disk at audit time. No GPU device is present. CPU-first tooling is supported; no paid compute is used.

## Task and candidates

Visible stairs, pathway obstruction, damaged pavement and ramp obstruction are proposed image-level observations. Labels do not measure slope/width, establish geolocation, identify permanence or prove route safety. Their dataset coverage is unresolved.

| Resource / architecture | Audited state and decision |
| --- | --- |
| Local annotated image-level data | Absent; cannot train/evaluate or establish class balance, duplicates, license, scene coverage or generalization |
| Local bounding-box/pixel annotations | Absent; no detection/segmentation or localization claim |
| Generic ImageNet/COCO weights | No approved hazard-specific ontology/evaluation; not downloaded or presented as recognizing these hazards |
| Small CPU image classifier | Conditional executable baseline for a future licensed single-label manifest, not a validated model selection or trained product |
| Detector/segmenter | Deferred until licensed localization annotations and requirements exist |

The supported conditional baseline is `pathable-small-cnn-v1`: a fixed small convolutional classifier, RGB resize preprocessing and safe tensor assets. It trains from scratch; transfer learning remains a later measured choice after a real dataset audit. This choice makes executable CPU training/inference possible without falsely claiming that generic pretrained classes solve accessibility detection. Multi-label/detection data must not be silently coerced into this single-label contract.

## Dependency evidence

Official CPU index reports torch 2.14.1+cpu; its Python 3.12 Linux x86_64 wheel was downloaded from the index's actual `download-r2.pytorch.org` endpoint (196.3 MB). Public PyPI metadata reports NumPy 2.5.4 (Python >=3.12) and safetensors 0.8.0 (Python >=3.10). The optional environment uses a hash lock and safe tensor state dictionaries, never uploaded pickle/code. Backend core dependencies remain separate. PyTorch metadata lists Apache/BSD/MIT-family licenses; NumPy lists BSD/0BSD/MIT/Zlib/CC0. Dependency licensing does not establish dataset or weights rights. Installed package license records accompany the optional environment; model registration requires its own license/provenance manifest.

## Exact missing requirements

Provide a licensed, privacy-reviewed image collection with class definitions, per-image SHA-256, campus/scene/capture group IDs and nonleaking train/validation/test assignments. Supply enough distinct groups/classes for meaningful held-out evaluation, then run the actual training/evaluation tools and review results/limitations. Register checksum-matching safe tensor weights, immutable preprocessing/class vocabulary and the held-out evidence bundle. Until then `/ml/status` is unavailable and inference submission returns typed 503; manual reporting and routing remain functional.

Synthetic images/weights may test serialization, tensor execution and review isolation only. Their outputs must never be registered as a product model or reported as measured hazard accuracy.

## Public candidate metadata checked

The upstream [RoadDamageDetector README](https://github.com/sekilab/RoadDamageDetector) links RDD2022, with JPEG/XML Pascal VOC training annotations from six countries and regional downloads ranging from hundreds of MiB to a 9.9 GB Norway archive. This is a road-damage detection candidate, not an established campus stairs/ramp/pathway-obstruction dataset. Source images, annotation quality, class balance and grouped leakage were not downloaded or verified. The repository LICENSE is MIT for software/documentation; it is not assumed to license linked dataset images. The linked [Figshare dataset](https://figshare.com/articles/dataset/21431547) license metadata request at api.figshare.com returned proxy 403 under current network policy, so dataset licensing remains unverified. No network policy was broadened or dataset/weights downloaded for this candidate.

The official [torchvision category metadata](https://github.com/pytorch/vision/blob/main/torchvision/models/_meta.py) was inspected: ImageNet's 1,000 categories and COCO's 91 indexed entries do not declare the four exact target hazard labels. Related objects cannot substitute for hazard-specific annotation/evaluation. Generic weights remain unselected. These source checks identify candidates and limits; they do not establish that no suitable dataset exists anywhere.
