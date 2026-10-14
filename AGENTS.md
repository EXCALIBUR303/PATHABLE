# PathAble working agreement

Read `docs/PROJECT_STATUS.md`, `docs/IMPLEMENTATION_PLAN.md`, and the relevant contracts before changing the project. Inspect actual code and tests; status prose alone is not implementation evidence.

- The user authorized Phase 8 with “continue” after the Phase 7 handoff. Current authorization covers the independent final audit and scoped repairs. At its boundary, record evidence, save files, give the completion report and stop for further direction.
- Each cloud task already has an isolated workspace. Work in the existing checkout. Do not create Git worktrees unless explicitly requested.
- Preserve working files and approved contracts. Record material design changes in an ADR. Do not regenerate working modules needlessly.
- Never push or deploy without explicit authorization. Saving files does not imply publishing the environment or making a Git commit.
- Keep secrets, image uploads, model weights, datasets, generated environments, and local databases out of Git.
- Synthetic data must say `synthetic_demo`; never imply verified real university infrastructure.
- Unknown measurements are nullable values, never zero-filled or interpreted as accessible. Hard constraints remove edges. AI suggestions never authorize infrastructure changes.
- Keep the routing engine independent of HTTP, ORM, and map presentation. All route calculations use a consistent graph revision and explicit cost-model version.
- Authorization, ownership, optimistic concurrency, and audit records are server responsibilities.
- Record exact validation commands, counts, failures, skips, and unrun checks. No invented test evidence. Phase 0 has design checks only.
- Model changes are performed manually by the user. Do not claim to have switched model or effort. If runtime identity is not available, say it is unverified rather than inferring it from the requested model.
