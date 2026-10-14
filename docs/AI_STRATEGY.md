# Optional AI/ML strategy

Phase 5 implements the conditional CPU pipeline, approved asset registry, private durable jobs and annotation review. No licensed hazard dataset or evaluated product weights are available; inference remains disabled. [Resource audit](ML_RESOURCE_AUDIT.md), [ADR-014](adr/014-phase5-optional-ml.md) and [executed evidence](PHASE5_TEST_EVIDENCE.md) distinguish integration from trained capability. Synthetic fixtures exercise execution only.

## Task and selection gate

Candidate labels: visible stairs, pathway obstruction, damaged pavement, ramp obstruction. These are visual observations, not proof that a particular person can pass a pathway. A single image cannot reliably measure slope, clear width, unseen entrances, permanence or overall route safety. Link any predicted observation to the uploaded evidence and reported location; do not infer geolocation from scenery.

Before selecting a model in Phase 5, audit candidate datasets for access, consent/privacy, license and redistribution, annotation format, class ontology, scene diversity, image quality, duplicates, imbalance and domain mismatch. No generic COCO model is assumed to recognize specialized ramp obstruction or pavement accessibility. Establish a dataset card and manifest with hashes, split/group IDs and provenance; external datasets stay outside Git.

| Alternative | Appropriate condition | Tradeoff / gate |
| --- | --- | --- |
| Image classification with PyTorch/torchvision transfer learning | Only image-level hazard labels and no localization promise | Simpler CPU inference; cannot produce reliable object boxes or proof of route blockage |
| Object detector, e.g. torchvision Faster R-CNN baseline | Licensed bounding-box annotations and UI needs hazard location | More annotation/compute, box matching and detection metrics required |
| Segmentation architecture | Pixel-level damage/obstruction labels with a defined measurement objective | Highest labeling/compute complexity; defer unless justified |

Choose the smallest architecture that meets measured requirements. Check torchvision/PyTorch version compatibility, license, checksum and expected preprocessing. CPU-first inference is a portability requirement; acceleration is optional and must not block navigation. Do not purchase compute or assume a GPU exists. Model architecture remains explicitly unresolved until data is audited; this is intentional Phase 5 work, not a Phase 0 blocker.

## Pipeline boundaries

`ml/datasets/`: licensed manifest, loaders and split logic. `ml/training/`: configuration, seed/reproducibility, checkpointing. `ml/evaluation/`: immutable held-out evaluation and report generation. `ml/inference/`: preprocessing/adapter/versioned outputs. Core FastAPI stores jobs; a separate optional worker reads ready private evidence, safely loads approved weights and writes predictions. Worker leases use DB `FOR UPDATE SKIP LOCKED`, bounded retry and timeout; no broker required initially.

Adapter input: private evidence reference, content hash, model version, preprocessing version; not an arbitrary file path supplied by a client. Output: model/dataset/weights hashes, class vocabulary, scores, optional normalized boxes, latency, failure code, timestamp. Store per-image dimensions after normalization so boxes can be transformed correctly. Prediction scores are model scores, not necessarily calibrated probabilities and never safety guarantees.

Statuses distinguish disabled, missing dataset, missing weights, invalid image, incompatible weights, timeout and inference failure. `/ml/status` returns availability plus reason; unavailable inference requests return a typed 503 while navigation and manual reporting continue. Successful job completion requires real persisted outputs from real weights. Do not return random labels, canned predictions, or synthetic metrics as model behavior. Synthetic fixtures may test adapters only and must be explicitly labeled as test doubles.

## Evaluation design

Split by campus/scene/capture session before augmentation, with perceptual/exact deduplication across splits. Keep held-out evaluation inaccessible to threshold/model tuning. Record counts by class and split, source license, class definitions, preprocessing, code revision, random seed, hardware, training schedule and asset hashes.

Classification: per-class precision/recall/F1, support and confusion matrix. Detection: matching/IoU protocol, AP/mAP and per-class precision/recall at declared score/IoU thresholds; do not report image classification accuracy as localization quality. Include abstention/uncertain cases, false positives/negatives and confidence calibration where feasible. Report real counts and intervals where sample size supports them; avoid impressive aggregates hiding rare hazards. Domain generalization requires new-campus evaluation, not only random image splits.

No fixed accuracy claim before a dataset is available. Phase 5 acceptance is either evaluated functioning inference with reproducible assets and honest limitations, or an explicitly disabled integration/training pipeline with the exact missing resource listed and tests proving core app independence. A missing-resource branch must be reported as limited/blocked ML capability, never equivalent to successful training.

## Human review contract

Admins see original normalized evidence, proposed class/box, model identity, score explanation and accept/reject controls. Accepting a prediction only records annotation review. An admin must separately verify the report, confirm affected edges and specify a restriction to change graph state. Worker DB permissions must not allow direct restrictions/graph-state changes. Required test F proves that any unreviewed or merely accepted prediction cannot block routing.

## Implemented conditional baseline

`ml/pathable_ml` implements rights/hash/group/perceptual split checks, fixed RGB 128px preprocessing, a small CPU classifier trained from scratch, deterministic validation-only checkpoint selection, one-time held-out classification evaluation, safe tensor loading and score-margin abstention. This is a supported single-label baseline for future annotations, not evidence that it is suitable for a real hazard dataset. Localization and transfer-learning selection remain unresolved until actual data/requirements are reviewed. See [ML commands](../ml/README.md).

Models are registered only through an explicit owner CLI after evaluation/license review. Runtime activation additionally requires configuration, validated immutable assets and a separate restricted worker. CPU dependencies are hash-locked in an optional environment and do not enter core routing/reporting. Product activation rejects synthetic fixtures. Admin prediction acceptance remains annotation-only; critical F now has real DB/browser evidence. No real hazard precision, recall, F1, calibration or generalization was measured.
