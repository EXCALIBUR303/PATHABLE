# ADR-014 — Optional CPU classification, evaluated assets and isolated review

Accepted 2026-10-13 for the Phase 5 resource-limited integration, with [executed evidence](../PHASE5_TEST_EVIDENCE.md). [Resource audit](../ML_RESOURCE_AUDIT.md) finds no licensed labeled data or evaluated hazard weights. Core routing/reporting remains independent of tensor dependencies and resource availability.

Provide a conditional fixed small CPU single-label classifier, group/hash/perceptual leakage audit, deterministic training/validation checkpoint selection, immutable held-out evaluation and safe tensor bundles. This is an executable baseline, not a validated architecture choice for nonexistent annotations. No localization claim or generic pretrained hazard labeling. Registration rejects synthetic fixtures and requires matching license/provenance/evaluation hashes; public inference stays disabled without approved resources.

The core API stores versioned jobs/predictions and authorizes private evidence. An optional worker uses a separate restricted database role, short SKIP LOCKED leases and bounded retries; tensor/image execution occurs in a timeout/resource-limited child process without DB credentials. Jobs pin immutable model/evidence hashes and stale leases cannot publish. Prediction review records annotation/audit only and never invokes graph mutation. A separate report verification transaction remains required for restrictions. Critical F must verify proposed and accepted predictions leave routes/restrictions/revisions unchanged.

Use a separate hash-locked Linux x86_64/Python 3.12 CPU environment. No CUDA dependencies, paid compute, untrusted pickle weights or implicit model downloads. Mac optional ML portability and trained-model metrics remain unverified.

Final DB-role execution uses a shared advisory content lock with pending evidence deletion so the worker retains SELECT-only evidence access. CPU fixture training is reproducible, while no actual hazard model or accuracy is claimed. Default analysis stays unavailable; annotation and report verification remain independent user actions.
