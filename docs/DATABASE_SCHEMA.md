# Database schema

Implemented through Phase 4 in SQLAlchemy and Alembic: Phase 1 foundation (15 tables) plus reports, evidence, restriction ledger, idempotency and stream leases (seven tables, 22 total). Phase 5 adds model_versions, inference_jobs and predictions (25 tables total); head is `0003_ml`. Model activation is unavailable without real evaluated assets. PostgreSQL 17 + PostGIS 3.5 is running and tested. Names below are canonical snake_case database names. API identifiers are UUID strings; graph versions and event IDs are decimal strings to avoid JavaScript integer truncation.

## Shared rules

Use UUID primary keys, UTC `timestamptz`, non-null `created_at`/`updated_at`, and integer `row_version >= 1` on mutable resources. FKs default to RESTRICT. Use explicit child cleanup for sessions and evidence after authorization/retention checks; never cascade-delete audit records. Enums are constrained text with migration-managed values. No client controls timestamps, reviewer IDs, roles, verification, graph versions, or audit values.

Measurements use double precision with explicit finite checks and unit bounds; JSON NaN/Infinity is invalid. Unknown is NULL, never zero. No nullable measurement is automatically converted into verified accessibility. Cross-row rules use service validation plus deferred constraint triggers where described; a CHECK cannot safely query another row.

All campus-owned resources include `campus_id`; composite unique `(campus_id,id)` and composite FKs prevent cross-campus associations. The initial UI supports one active synthetic campus, not multi-tenant customer administration. Coordinate geometries are SRID 4326, two-dimensional, nonempty, valid, and in WGS84 longitude/latitude ranges. Geography calculations operate on these geometries cast to `geography`.

## Identity and preferences

| Table | Fields and relationships | Constraints / indexes |
| --- | --- | --- |
| users | id, normalized_email, display_name, password_hash, role (`user`,`admin`), active, auth_version, timestamps, row_version | Unique normalized email; trim/lower policy is explicit (no provider-specific dot removal); registration cannot set role; inactive users cannot authenticate |
| auth_sessions | id, token_hash, nullable user_id → users, issued_auth_version, created_at, expires_at, last_seen_at, revoked_at | Unique cryptographic token hash; anonymous sessions for pre-login CSRF; index user_id and expiry; never store raw session tokens; derive CSRF token as specified in security design; rotate session on login; absolute TTL 7 days, idle TTL 24h, anonymous TTL 30min |
| accessibility_profiles | id, user_id → users (unique), avoid_stairs, max_slope_pct nullable, min_width_m nullable, excluded_surfaces text[], unknown_policy, travel_speed_mps, timestamps, row_version | max slope [0,100], width (0,10], speed [0.1,3]; no NaN/Infinity; allowed surface enums only; unknown policy `exclude` / `allow_with_warning`; no diagnosis field |
| saved_destinations | id, user_id → users, campus_id, location_id → locations, label, created_at | Unique (user_id,location_id); user-scoped queries and deletion |

Rate limits initially use transactional DB counters (`rate_limit_buckets`: scope, keyed identifier hash, bucket_start, count, expires_at; composite PK). Hash identifiers with a separately supplied application key; never retain raw IPs beyond operational necessity. Add cleanup and global storage caps. A public distributed deployment may replace this adapter later; do not trust client-provided forwarding headers without a known proxy configuration.

## Campus graph

| Table | Fields and relationships | Constraints / indexes |
| --- | --- | --- |
| campuses | id, name, data_origin (`synthetic_demo`,`surveyed`), attribution, default_timezone, boundary Polygon nullable | Only `synthetic_demo` seeded; no Woxsen verification claim; GiST boundary |
| locations | id, campus_id → campuses, name, kind, description, point Point, active, row_version | GiST point; btree campus/name; no routing from centroid without an access point |
| path_nodes | id, campus_id, name nullable, point Point, level smallint, active, row_version | GiST point; same XY on different levels are separate nodes |
| location_access_points | campus_id, location_id → locations, node_id → path_nodes, label, kind (`entrance`,`junction`), is_primary | Composite PK (location_id,node_id); one partial-unique primary per location; same campus; selectable endpoints are explicit |
| path_edges | id, campus_id, source_node_id, target_node_id → path_nodes, geometry LineString, distance_m, direction (`both`,`forward`,`reverse`), active, width_m nullable, slope_pct nullable, surface, has_stairs nullable, has_ramp nullable, accessibility, availability, verification, verified_at nullable, verified_until nullable, verified_by nullable → users, provenance, row_version | Source != target; distance > 0; width (0,10]; signed slope [-100,100]; finite values; indexes campus/source, campus/target and GiST geometry; directed arc IDs derive from physical edge ID and orientation |
| infrastructure | id, campus_id, location_id nullable, kind (`ramp`,`stairs`,`entrance`,`elevator`,`pathway`), name, point Point, active, accessibility, availability, verification, verified_at/until/by, provenance, row_version | Same status independence as path_edges; GiST point; absence of an edge mapping is visible, not silently ignored |
| infrastructure_edges | campus_id, infrastructure_id → infrastructure, edge_id → path_edges | Composite PK; M:N mapping; updates change graph revision; referenced nodes/edges soft-retire rather than deleting history |
| graph_state | campus_id PK → campuses, version bigint >=1, cost_model_version, policy_version, next_expiry_at nullable, updated_at | Exactly one row per campus; serialized graph writes use SELECT FOR UPDATE |

Status enums remain separate:

- Accessibility: `accessible`, `inaccessible`, `unknown`. A label is descriptive, not a substitute for user-specific numeric constraints.
- Availability: `open`, `closed`, `temporarily_blocked`. Stored here is the administrative baseline. Effective availability also includes active restrictions and mapped infrastructure.
- Verification: `verified`, `unverified`, `needs_review`. Verified records require reviewer, provenance, `verified_at <= verified_until`, and a nonexpired verification window to be considered current. Synthetic provenance may be internally verified **only as fictional demonstration data**.
- Surface: `smooth`, `uneven`, `gravel`, `unknown`. `unknown` is an explicit enum; unknown numeric/boolean fields remain NULL.

Path endpoints equal their node coordinates exactly after import normalization. Compute `distance_m = ST_Length(geometry::geography)` on geometry changes, never trust a client distance. A deferred trigger/service validates endpoint coordinates, same-level edges unless a supported vertical connector is explicit, geometry validity, and the ECEF endpoint-chord lower bound. Reject invalid records rather than quietly repairing distances. No self-loops, zero-length edges, or parallel duplicate geometries in the seed; legitimate parallel physical paths have distinct IDs and provenance. Moving a node requires updating all incident geometry in the same transaction.

## Reports, evidence, and review

| Table | Fields and relationships | Constraints / indexes |
| --- | --- | --- |
| obstacle_reports | id, campus_id, reporter_id → users, category, description, point Point, location_id nullable, infrastructure_id nullable, status, reviewer_id nullable, reviewed_at nullable, resolution_note nullable, resolved_at nullable, row_version, timestamps | Categories in API contract; description 10–2000 chars; point within supported campus boundary; indexes campus/status/created_at and reporter_id; legal transitions in service |
| report_edges | campus_id, report_id → obstacle_reports, edge_id → path_edges | Composite PK; reporter suggestion is not a restriction; admin confirms affected physical edges at verification |
| report_status_events | id, report_id, from_status nullable, to_status, actor_id nullable, note, occurred_at, resulting_row_version | Append-only history; index report_id/time; durable `submitted` and `pending_review` events |
| report_evidence | id, report_id, uploader_id, storage_key, media_type, byte_size, width_px, height_px, sha256, status (`processing`,`ready`,`rejected`,`deleted`), failure_code nullable, created_at | Private opaque storage key unique; max 3 ready/processing images per report; no client filename as storage path; bytes <=10 MiB, decoded pixels <=20M; stream/decoder validation required |
| edge_restrictions | id, campus_id, report_id nullable, edge_id, kind (`closed`,`temporarily_blocked`), reason, created_by, created_at, released_by nullable, released_at nullable | Partial unique (report_id,edge_id) for active non-null report source; active means released_at IS NULL; index edge_id WHERE active; manual restrictions have null report_id and explicit release action |
| admin_actions | id, actor_id → users, action_type, resource_type, resource_id, before_json, after_json, reason, request_id, graph_version nullable, created_at | Append-only, no API edit/delete; restrict database application role from UPDATE/DELETE; JSON contains allowlisted metadata, no evidence bytes or auth values |
| idempotency_records | id, actor_id, operation, key, request_hash, result_status, result_json, expires_at | Unique (actor_id,operation,key); fixed 24h TTL; response contains only authorized data; same key/different payload returns 409 |

Verification of a blocking report requires at least one confirmed edge, either selected directly or resolved from mapped infrastructure. Empty or ambiguous mappings return 422; a report can remain pending until mapping is corrected. Applying every active restriction matters: resolving report A releases only A's restrictions and must not reopen an edge still closed by B or a baseline/infrastructure condition. Supported concerns all use `verified` to mean a routing-relevant confirmed hazard; informational nonhazards are rejected with an explanation, not marked verified without a routing effect.

## Durable events and optional ML

| Table | Fields and relationships | Constraints / indexes |
| --- | --- | --- |
| graph_events | campus_id, graph_version, event_type, changed_edge_ids UUID[], reason, occurred_at | PK (campus_id,graph_version); insert in same transaction as graph mutation; event ID is version; no identities/images in public SSE payload; retain 7 days; replay older cursors triggers reset |
| inference_jobs | id, evidence_id, requested_by, model_version_id nullable, status (`queued`,`running`,`succeeded`,`failed`,`unavailable`), attempts, leased_until nullable, error_code nullable, timestamps | Worker lease via SKIP LOCKED; unique evidence/model; max three attempts; 120-second lease with token; short transactions; never blocks manual reports |
| model_versions | id, name, architecture, weights_sha256, dataset_manifest_hash, code_revision, license_summary, preprocessing_json, evaluation_json, evaluated_at, enabled | No enabled model without verified weights/license/evaluation; reports may exist with no model record |
| predictions | id, job_id, evidence_id, model_version_id, class_name, score, box_xyxy nullable, status (`proposed`,`accepted`,`rejected`), reviewer_id nullable, reviewed_at nullable | score [0,1], normalized boxes [0,1] with ordered bounds; accepting prediction annotates review only; official restrictions require report verification transaction |

## Transaction and migration policy

Migrations create extension/schema/indexes/constraints and never hide a reset. App role has limited DML; migration role performs DDL. Seed only with explicit synthetic flag; deterministic UUIDs and natural keys make reruns idempotent. Do not overwrite user edits during reseeding: existing seeded rows with unexpected versions cause an explanatory failure. Wrap one campus seed in a transaction; verify node geometry, reachability, alternative paths, and initial graph event/version consistency.

Graph-changing lock order: campus graph_state → affected reports in UUID order → infrastructure in UUID order → physical edges in UUID order. Use `WHERE row_version = expected` for CAS, increment each affected resource version once, check affected-row counts. Unique idempotency-key claim occurs before domain locks and within the same transaction; rollback discards incomplete records. No nested endpoint commits. See [transaction sequence](REPORTING_AND_EVENTS.md).

Readers load the campus version, all eligible data, active restrictions and future expiry under one repeatable-read transaction, then run pure routing on its immutable snapshot. Expiry maintenance occurs in a separate preceding transaction under the same graph lock. Data cannot mutate underneath the engine. Add indexes based on explain plans; never replace PostGIS integration tests with SQLite.

## Phase 4 integrity and retention

`sse_leases` stores UUID lease ID, keyed identity and expires_at with an expiry index. Short polling refreshes a 45-second lease; transactional admission enforces three per identity and 200 globally. Owner maintenance expires leases and 24-hour idempotency records. These are configured bounds, not a capacity measurement.

Migration 0002 validates report points inside a supported non-null campus boundary, immutable submitted report content and legal transitions, immutable restriction sources/final releases, same-campus references, and ready evidence dimensions/hash. Deferred checks require each verified report to have an active restriction and pending/rejected/resolved reports to have none; incomplete idempotency claims cannot commit. User/report locks serialize three active evidence slots and user storage reservations. Service CAS is required for evidence changes.

Report status history and admin audit remain append-only. Graph events cannot be updated, including by the owner. The narrow retention exception allows the table owner to delete only events older than seven days; application-role UPDATE/DELETE remains revoked. Reporting-semantics migration advances each existing campus revision with graph.reset, retaining edited data. Upgrade preservation and retention guards are tested in [Phase 4 evidence](PHASE4_TEST_EVIDENCE.md).

## Phase 5 implementation details

Model versions pin private UUID bundle_key, immutable manifest/weights/dataset hashes, preprocessing/class vocabulary and evaluation/code/license metadata. Only the owner registration CLI can write model records; runtime app and worker have SELECT only. At most one model is enabled; test_fixture models cannot be enabled. No product model record is registered in the development DB.

Inference jobs include immutable report/evidence/requester/model/hash lineage, lease_token/leased_until, next_attempt_at, error_code, latency_ms and abstained. Same-report evidence FK and prediction composite job/report/evidence/model FK prevent mismatched references. Unique evidence/model jobs and job/class predictions prevent duplicate work/output. Terminal jobs and prediction provenance are immutable; annotation review increments its row version and permits only proposed→accepted/rejected. Classification box_xyxy must be null and scores finite in [0,1].

The worker role may SELECT models/evidence/jobs/predictions, UPDATE jobs and INSERT proposed predictions; it has no graph/restriction/evidence/review/model modification privilege. Shared advisory locking coordinates evidence deletion and publication without granting evidence UPDATE. Backend tests create/drop their own UUID worker role so they do not alter development worker credentials. Migration 0003 has no graph reset because prediction annotations do not change routing semantics. See [Phase 5 evidence](PHASE5_TEST_EVIDENCE.md).
