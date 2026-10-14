# Model schedule and continuation

The user performs all model and reasoning-effort switches. There is no verified mechanism here to inspect or change the active model/effort. Phase 0 was requested as GPT-6 Astra / Extra High; do not misreport that preference as verified runtime metadata. If a setting is unavailable in the user's interface, choose the highest suitable available setting and record the deviation.

| Phase | Model | Effort | Change from prior requested phase |
| --- | --- | --- | --- |
| 0 Architecture | GPT-6 Astra | Extra High | Initial authorization |
| 1 Backend/database/auth | GPT-6.1 Sol | High | Model + effort |
| 2 Frontend/maps | GPT-6.1 Sol | High | No switch; authorization still required |
| 3 Routing | GPT-6 Astra | Max | Model + effort |
| 4 Reporting/live updates | GPT-6.1 Sol | High | Model + effort |
| 5 AI/ML | GPT-6 Astra | Extra High | Model + effort |
| 6 Integration/security | GPT-6 Astra | High | Effort only; authorization required |
| 7 Deployment preparation | GPT-6.1 Sol | Medium | Model + effort |
| 8 Final audit | GPT-6 Astra | Extra High | Model + effort |

Optional GPT-6 Luna / Low or Medium is only for explicitly delegated isolated simple work; it does not replace phase owners. Do not automatically spawn agents or switch models. Older models require user request or unavailability of the preferred model, with that reason recorded.

At each boundary: complete authorized work, run relevant checks, fix scoped defects, update status/evidence, save actual files, give the requested completion fields and continuation prompt, **stop**. Never continue just because the next phase uses the same model. No push or deployment without explicit authorization.

## Current handoff: final audit completed

Phase 8 independently inspected code and current results, repaired six findings and mapped all final success criteria. See the [final audit](FINAL_ENGINEERING_AUDIT.md). No Phase 9 is defined. Stop for a specific user-selected follow-up scope. For further audit/remediation, the recommendation is **GPT-6 Astra — Extra High**, unchanged from the requested Phase 8 settings; actual runtime remains unverified. Suggested continuation:

> Read docs/FINAL_ENGINEERING_AUDIT.md and PROJECT_STATUS.md. Address this follow-up scope: [specific chosen item]. Preserve all verified routing, authorization, recovery and privacy contracts, synthetic provenance and disabled trained ML. Test the affected workflows, update evidence and stop. Do not commit, push, deploy or publish.

## Historical Phase 1 continuation prompt

After manually selecting **GPT-6.1 Sol — High**, send:

> Continue PathAble Phase 1. Implement the backend and database foundation according to the approved architecture. Read AGENTS.md, docs/PROJECT_STATUS.md, docs/IMPLEMENTATION_PLAN.md, and the relevant contracts first. Preserve the Phase 0 design and existing work; record justified changes in an ADR. Run all relevant tests, save tested cloud setup/start instructions, update status and evidence, and stop at the next phase boundary. Do not push or deploy.

Phases 1–8 were subsequently authorized by the user's “continue” messages after their respective handoffs. The next agent must inspect actual files, current status and new user direction before starting follow-up work. Prediction acceptance cannot directly change route eligibility; official restrictions still require the report verification transaction.
