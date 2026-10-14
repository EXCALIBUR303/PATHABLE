# PathAble frontend

Phase 2 implements the landing page, interactive synthetic campus map, authentication, accessibility preferences, saved places/dashboard and role-protected infrastructure editing. Phase 3 adds complete trip preferences, Dijkstra/A* selection, primary/alternative routes, backend geometry/text directions, actual totals and uncertainty warnings. Known graph changes, expired observations, changed inputs and failed currentness checks retire the shown route. Phase 4 adds real private reporting/evidence/history, versioned admin review, database-backed analytics/audit and cookie-only live graph streaming. Recalculated routes after live changes require confirmation; drafts preserve their original versions. Phase 5 adds honest image-analysis status, private observations and annotation review with original-version drafts. Trained assets remain unavailable; accepting an annotation does not verify a report or change routes.

Use Node 24 and the saved npm lock. From the repository root:

```sh
bash scripts/install.sh
bash scripts/start.sh
bash scripts/test_frontend.sh
```

Startup owns the Vite process and validates compilation, same-origin API proxy and actual graph data. See [development setup](../docs/DEVELOPMENT.md) for service management and browser prerequisites. Individual frontend commands:

```sh
npm ci
npm run api:check
npm run typecheck
npm run lint
npm run format:check
npm test
npm run build
npm run test:e2e
```

Run these from `frontend/`. `api:generate` deliberately regenerates `src/types/api.generated.ts` after an approved backend/OpenAPI change; `api:check` compares without rewriting source. The build splits page/map/chart modules. `npm run preview` exercises the production build with the same development API proxy; it is not a production reverse proxy or deployment.

`src/app` owns session/query/router providers; `features` owns reusable workflows; `pages` composes screens; `services` wraps generated contracts and in-memory CSRF; `components` owns Radix primitives/map/status views; `styles` owns semantic tokens. Secrets and session tokens are never stored in browser storage. Root `.env` is private: only intentionally public `VITE_` settings may reach the client. Never prefix database/session secrets with `VITE_`.

The Leaflet canvas draws backend GeoJSON without external tiles by default. Optional tile URL and attribution must both be supplied in the root environment; review provider licensing/hosts before enabling. Map measurements remain unknown when absent. Entrance selection uses node IDs, and text views accompany locations/pathways.

Original vector brand assets are in `src/assets/` and `public/favicon.svg`. Inter is self-hosted through `@fontsource-variable/inter`; its SIL Open Font License is retained in `public/licenses/inter-OFL.txt`. No remote font or paid service is needed. Validation and inspected screenshots are recorded in [Phase 2 evidence](../docs/PHASE2_TEST_EVIDENCE.md) [Phase 3 evidence](../docs/PHASE3_TEST_EVIDENCE.md) and [Phase 4 evidence](../docs/PHASE4_TEST_EVIDENCE.md).

[Phase 5 evidence](../docs/PHASE5_TEST_EVIDENCE.md) records the unavailable/annotation component checks and real DB/browser review using explicitly labeled synthetic doubles.
