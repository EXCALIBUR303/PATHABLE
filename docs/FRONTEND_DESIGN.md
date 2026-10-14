# Frontend and product design

Phase 0 design system and behavior plan, with Phase 2 implementation now validated. Actual SVG brand assets, semantic CSS tokens, React pages, Radix primitives, typed API client and live synthetic map are in `frontend/`. Phases 3 and 4 implement routing, private report submission/history, review/analytics and live SSE-driven currentness; Phase 5 adds honest optional-ML status and annotation review; trained hazard assets remain unavailable. See [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md) and [ADR-013](adr/013-phase4-reporting.md). See [Phase 2 evidence](PHASE2_TEST_EVIDENCE.md) and [ADR-011](adr/011-phase2-frontend.md) for implemented scope and deviations from the initial candidate toolchain.

## Brand and accessible visual system

PathAble — “Every Path Should Be Possible.” Design a vector mark from two connected path strokes and a deliberate junction, suggesting an inclusive continuous journey; do not use a generic standalone pin. Phase 2 creates primary wordmark, compact SVG mark and favicon with accessible naming and monochrome variants. Use Inter, self-hosted with its license, with system sans-serif fallback; no remote font dependency is required.

Proposed semantic tokens (validate final rendered states, not only swatches):

| Token | Value | Intended use |
| --- | --- | --- |
| canvas | #FAF9F6 | Warm-white page/map fallback |
| surface | #FFFFFF | Forms, overlays and panels |
| text | #163C3A | Body and headings |
| text_muted | #4C6360 | Secondary text |
| primary | #0B625A | Deep-teal main action/selected route |
| on_primary | #FFFFFF | Action text |
| sage | #DCE9DF | Subtle secondary panels with text color |
| accent | #285F8F | Alternative route and information |
| warning | #7A4B00 | Warning text/icon on #FFF1CC |
| danger | #A82D35 | Error/closure text/icon on #FFF0F0 |
| boundary | #718B85 | Interactive boundaries/focus where contrast required |

Use a 4px spacing base (8/12/16/24/32/48 typical), 8–12px radii, subtle neutral shadow, 16px body, 1.5 line-height, clear heading hierarchy and tabular numbers for route metrics. Target WCAG 2.2 AA: text contrast >=4.5:1 for normal text, focus/control boundaries >=3:1 as applicable; verify against every actual background. Targets at least 24×24 CSS px with spacing, prefer 44px controls. No status conveyed by color alone. Reduced motion disables route-drawing/entry animation; normal motion 120–200ms and never required to understand changes.

Routes: selected teal solid, alternatives blue dashed with distinct numbers, unavailable red barred segments, uncertain amber dotted segments with textual warning. Location markers use icon+label; verified is a provenance badge, not a safety shield. Lucide provides a consistent stroke style; decorative icons aria-hidden and icon-only buttons explicitly named. Avoid ambiguous “accessible” badges where user-specific measurements are required.

## Application composition

`app/`: router, providers, error boundary, session bootstrap and design tokens. `features/`: auth, navigation, profile, reports, admin, saved destinations. `services/`: typed API client, SSE client, generated contracts. `components/`: shared primitives, form errors, accessible tables, status banners. `pages/`: route composition only. `hooks/`: reusable interaction/network hooks. `types/`: frontend-only view models, not duplicate hand-maintained API schemas. Server state belongs to TanStack Query; ephemeral map selection/form state stays local. No global state library until demonstrated need.

Use shadcn source components on Radix primitives, Tailwind tokens, Lucide, Motion, React Leaflet and Recharts. Native semantics first. Generate API TypeScript types from FastAPI OpenAPI after Phase 1 and fail checks on drift. Fetch wrapper includes same-origin credentials, CSRF headers, abort signals, structured problem parsing and request IDs. Mutations invalidate exactly relevant query keys. Browser tests exercise live APIs; MSW/fixtures may isolate component tests but never masquerade as production services.

## Page behavior

| Page | Responsibilities and unavailable/error states |
| --- | --- |
| Landing `/` | Hero, value proposition, product walkthrough, how it works, features and footer. CTA “Explore demo” navigates to map. Before Phase 3, preview explicitly labels route calculation unavailable. |
| Navigate `/navigate` | Left panel source/destination search and profile; dominant map center; contextual route alternatives/instructions panel. Source/destination select real access-point node IDs. Blank selections prevent submit. |
| Profile `/profile` | Save functional constraints through API, validate units/ranges, warn before enabling uncertainty, show save/pending/conflict states. Presets expose their actual values. |
| Reports `/reports` and `/reports/new` | Map or text location selection, category, description, evidence validation, submit; list own status/history. Failed evidence upload does not erase a submitted report. |
| Account `/dashboard` | Saved destinations, settings and own reports; API data with meaningful empty states. |
| Admin `/admin` | Queue, infrastructure maintenance, verified restrictions, audit and metrics; role-gated navigation plus server enforcement. Conflict 409 displays latest state and requires reconsideration. |
| Auth `/login`, `/register` | Labeled fields, password-manager support, generic login errors, clear registration validation, safe return-to allowlist. Logout revokes session. |

Laptop layout starts with 320px controls, flexible map, 320px contextual panel when space permits. Essential mobile flow uses stacked controls/map and a dismissible route detail sheet with focus handling. Keep text navigation usable even when Leaflet tiles/scripts fail. Keyboard users can select endpoints, submit, compare alternatives and read all instructions without manipulating the map. Map pins have equivalent searchable list entries; no information exists only on hover.

## Navigation interaction contract

UI never computes its own authoritative path, travel distance or duration. Render backend GeoJSON and totals; unit formatting may round display but retains raw values. Show demo origin persistently. Route comparison labels distance, duration estimate, uncertainty and verified-observation coverage distinctly. It never says “safe route.” A warning region uses polite aria-live for completed recalculation; urgent invalidation uses restrained assertive messaging without repeatedly stealing focus.

Search has keyboard combobox semantics, debouncing and cancellation. Loading controls remain identifiable; form input is preserved across recoverable failures. Source/destination swapping cancels old requests. A request-generation token prevents stale responses overwriting new user selections. SSE/version handling follows [reporting/events](REPORTING_AND_EVENTS.md). If the backend phase is unavailable, disable the affected control with an explanation instead of drawing fabricated route/report results.

Tile URL is optional and blank by default. Render real synthetic graph geometry on a neutral Leaflet map at known coordinates with explicit attribution. No verified Woxsen map or real-world navigation claim. If adding external tiles, review license/attribution/rate limits and configure exact hosts in environment settings; map failure leaves geometry and textual directions visible.

## UI verification gates

Phase 2: component tests for keyboard combobox, validation, network failures, role/ownership states, form focus and reduced motion; build/typecheck; Playwright with Phase 1 real login/profile/map reads. Phase 3: backend response-to-map geometry/totals parity, alternatives and no-route. Phase 4: report/evidence/admin/SSE full flow. Phase 6: automated axe plus manual keyboard, zoom/text reflow, contrast, focus order, dialogs and screen-reader announcements. Automated checks alone do not establish WCAG conformance.
