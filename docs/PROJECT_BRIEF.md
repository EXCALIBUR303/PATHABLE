# Original project brief

User-provided specification received 2026-10-12. Preserved for continuity; current authorization and implemented capabilities are recorded in [PROJECT_STATUS.md](PROJECT_STATUS.md). Requested model settings below are user preferences, not independently verified runtime metadata. Later explicit user authorization supersedes the initial Phase 0 boundary. Only trailing whitespace has been normalized.

---

# PATHABLE — COMPLETE PRODUCTION-ORIENTED DEVELOPMENT
# MASTER ENGINEERING PROMPT — VERSION 2.0

PROJECT NAME: PathAble
TAGLINE: Every Path Should Be Possible.

PROJECT CATEGORY:
AI + MACHINE LEARNING + FULL-STACK DEVELOPMENT
+ GRAPH ALGORITHMS + GEOSPATIAL SYSTEMS

CURRENT CODEX MODEL:
GPT-6 Astra

CURRENT REASONING EFFORT:
Extra High

INITIAL AUTHORIZED PHASE:
Phase 0 — Architecture and Critical Engineering Design


========================================================
01. YOUR ROLE AND RESPONSIBILITIES
========================================================

Act as an elite multidisciplinary software engineering
team responsible for building a complete application.

Assume the combined responsibilities of:

- Principal Software Architect
- Senior Full-Stack Engineer
- AI/ML Research Engineer
- Computer Vision Engineer
- Graph Algorithms Specialist
- Database and Geospatial Engineer
- Senior Product Designer
- Accessibility Engineering Specialist
- Application Security Engineer
- QA Automation Engineer
- DevOps Engineer

Your mission is to design, build, integrate, test,
refine, and prepare PathAble for deployment.

This must be a working software system rather than
a visually impressive but nonfunctional prototype.

The final product should demonstrate genuine
engineering quality, algorithmic correctness,
technical originality, and excellent UI/UX.

Treat this as a serious software project intended
for university demonstrations, hackathons,
portfolio presentations, and future research.

Do not optimize merely for the appearance of
project completion.

Optimize for actual correctness, usability,
reliability, and maintainability.


========================================================
02. MODEL SELECTION AND SWITCHING PROTOCOL
========================================================

CRITICAL INSTRUCTION:

This development will use multiple Codex models.

The available models include:

1. GPT-6.1 Sol
2. GPT-6 Astra
3. GPT-6 Sol
4. GPT-6 Luna
5. GPT-5.6 Sol
6. GPT-5.6 Terra
7. GPT-5.6 Luna

Use the strongest appropriate models according
to the schedule below.

Prioritize engineering quality over minimal usage.

However, do not waste expensive reasoning on
repetitive or straightforward work.

OFFICIAL DEVELOPMENT SCHEDULE:

PHASE 0
Task: Architecture and Critical Engineering Design
Model: GPT-6 Astra
Effort: Extra High

PHASE 1
Task: Backend, Database, Authentication, APIs
Model: GPT-6.1 Sol
Effort: High

PHASE 2
Task: Premium Frontend and Interactive Maps
Model: GPT-6.1 Sol
Effort: High

PHASE 3
Task: Intelligent Routing and Graph Algorithms
Model: GPT-6 Astra
Effort: Max

PHASE 4
Task: Reporting, Admin Dashboard, Live Updates
Model: GPT-6.1 Sol
Effort: High

PHASE 5
Task: AI/ML and Computer Vision
Model: GPT-6 Astra
Effort: Extra High

PHASE 6
Task: Integration, Security, Debugging, Testing
Model: GPT-6 Astra
Effort: High

PHASE 7
Task: Deployment and Documentation
Model: GPT-6.1 Sol
Effort: Medium

PHASE 8
Task: Comprehensive Final Engineering Audit
Model: GPT-6 Astra
Effort: Extra High

OPTIONAL MODEL:
GPT-6 Luna at Low or Medium for isolated,
straightforward documentation or repetitive tasks.

Use older models only when explicitly requested
or when the preferred models are unavailable.

IMPORTANT:

You cannot assume you can directly change the
active Codex model or reasoning effort.

I will manually perform all model switches.

At the end of every phase:

1. Complete the actual implementation.
2. Run appropriate tests.
3. Fix issues within the phase's scope.
4. Update the project status documentation.
5. Save all work.
6. Stop execution.
7. Tell me the exact next model.
8. Tell me the exact reasoning effort.
9. Provide a continuation prompt.
10. Wait for my authorization.

DO NOT silently continue into another phase.

DO NOT restart the project after changing models.

DO NOT regenerate working code unnecessarily.

DO NOT ignore the approved architecture.

If the specified reasoning effort is unavailable,
recommend the highest suitable setting available
in the user's Codex interface.

If the current model is already correct for
the next phase, say that no model switch is needed.

Still stop at the phase boundary.

If a phase fails its acceptance criteria,
do not pretend that it is complete.

Fix the problems or report the blockers.


========================================================
03. CRITICAL REASONING REQUIREMENTS
========================================================

For engineering-critical decisions, perform
careful technical analysis before coding.

Evaluate:

- Correctness
- Algorithmic complexity
- Data integrity
- System reliability
- Scalability
- Security
- Accessibility
- Maintainability
- Integration compatibility
- Failure conditions
- Technical tradeoffs

Do not blindly select technologies or algorithms.

For major architectural decisions:

1. Identify the problem.
2. Consider reasonable implementation alternatives.
3. Assess the tradeoffs.
4. Choose the most suitable approach.
5. Document the decision and justification.
6. Define validation criteria.

Provide concise engineering decision summaries,
not lengthy internal reasoning transcripts.

Maintain:

- Architecture Decision Records
- Risk Register
- Technical Assumptions
- Acceptance Criteria
- Implementation Status
- Test Evidence

IMPORTANT:

Identify possible failure scenarios before
implementing complex functionality.

For example:

What happens when:
- An accessible route does not exist?
- A ramp becomes unavailable?
- An infrastructure record is incomplete?
- An image is incorrectly classified?
- A pathway has unknown slope information?
- A user attempts an unauthorized operation?
- Two administrators update the same report?
- The database connection fails?
- The map service becomes unavailable?
- The user loses network connectivity?
- AI inference fails?
- A graph contains disconnected components?
- Two routing algorithms disagree?
- A route becomes unavailable during navigation?

Design explicit handling for these cases.

Never silently replace a failed computation
with fabricated results.


========================================================
04. PROJECT PROBLEM STATEMENT
========================================================

Traditional navigation applications generally
prioritize the shortest or fastest path.

However, shortest routes may contain:

- Stairs
- Inaccessible entrances
- Steep pathways
- Broken elevators
- Uneven surfaces
- Narrow walkways
- Blocked ramps
- Temporary obstructions

These conditions can create significant difficulties
for people with mobility impairments.

Develop an AI-assisted accessibility navigation
platform capable of calculating personalized
routes based on verified infrastructure data
and individual accessibility requirements.

The system must combine:

- Graph-based pathfinding
- Geospatial databases
- Accessibility constraints
- Community infrastructure reporting
- Administrative verification
- AI-assisted image analysis
- Dynamic route recalculation

The objective is to make navigation information
more inclusive, reliable, and actionable.


========================================================
05. PROJECT VISION
========================================================

Build PathAble as an intelligent campus navigation
and accessibility monitoring system.

The application should eventually support
real campuses, including Woxsen University.

However, begin with clearly labeled synthetic
demonstration infrastructure.

Do not fabricate verified university maps.

The final application should support:

USER CAPABILITIES:

1. Register and authenticate.
2. Explore an interactive campus map.
3. Search for locations.
4. Choose source and destination.
5. Configure accessibility preferences.
6. Calculate suitable routes.
7. Compare route alternatives.
8. View distance and estimated duration.
9. Receive route instructions.
10. View infrastructure accessibility information.
11. Report obstacles.
12. Upload supporting evidence.
13. Track submitted reports.
14. Save navigation preferences.
15. Receive updated route information.

ADMINISTRATIVE CAPABILITIES:

1. Review infrastructure reports.
2. Verify or reject reports.
3. Change infrastructure availability.
4. Manage pathway records.
5. Review accessibility data quality.
6. Monitor unresolved issues.
7. View accessibility analytics.
8. Track administrative actions.
9. Manage graph information.
10. Review AI-assisted detections.

All implemented features must be functional.


========================================================
06. TECHNOLOGY STACK
========================================================

FRONTEND:

- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Radix UI
- Lucide React
- Motion
- React Leaflet
- TanStack Query
- Recharts

BACKEND:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic

DATABASE:

- PostgreSQL
- PostGIS

ALGORITHMS:

- Dijkstra's Algorithm
- A* Search

AI/ML:

- PyTorch
- Appropriate computer vision architecture
- OpenCV if needed

TESTING:

- Pytest
- Vitest
- React Testing Library
- Playwright

DEVOPS:

- Docker
- Docker Compose
- GitHub Actions

Choose compatible stable versions.

Avoid unnecessary frameworks and dependencies.

Prefer technology that is maintainable,
well-supported, and appropriate for the task.


========================================================
07. SYSTEM ARCHITECTURE
========================================================

Use a modular monorepo.

Recommended structure:

pathable/
|
|-- frontend/
|   |-- src/
|       |-- app/
|       |-- components/
|       |-- features/
|       |-- pages/
|       |-- hooks/
|       |-- services/
|       |-- types/
|       |-- styles/
|       |-- assets/
|
|-- backend/
|   |-- app/
|       |-- api/
|       |-- core/
|       |-- db/
|       |-- models/
|       |-- schemas/
|       |-- repositories/
|       |-- services/
|       |-- routing/
|       |-- tests/
|   |-- alembic/
|
|-- ml/
|   |-- datasets/
|   |-- training/
|   |-- inference/
|   |-- evaluation/
|
|-- docs/
|-- scripts/
|-- .github/
|-- docker-compose.yml
|-- .env.example
|-- README.md
|-- .gitignore

Use a clear layered architecture.

Presentation Layer
       |
Application/API Layer
       |
Domain Services
       |
Routing / Reporting / AI Modules
       |
Persistence Layer
       |
PostgreSQL + PostGIS

The routing engine must be independently testable.

The AI module must remain optional.

The frontend must communicate with real APIs.

Do not tightly couple mapping visualization
with pathfinding logic.

Use typed API contracts and validation.


========================================================
08. DATABASE AND DATA INTEGRITY
========================================================

Design a normalized relational database.

Required entities:

- Users
- AccessibilityProfiles
- Locations
- PathNodes
- PathEdges
- Infrastructure
- ObstacleReports
- ReportEvidence
- AdminActions
- SavedDestinations

Add additional entities if justified.

For pathway edges, consider storing:

- Edge identifier
- Source node
- Destination node
- Geographic geometry
- Distance in metres
- Path width
- Slope percentage
- Surface material
- Stairs presence
- Ramp presence
- Directionality
- Accessibility classification
- Availability status
- Verification status
- Verification timestamp
- Last modification timestamp

Separate:

ACCESSIBILITY:
- Accessible
- Inaccessible
- Unknown

AVAILABILITY:
- Open
- Closed
- Temporarily blocked

VERIFICATION:
- Verified
- Unverified
- Needs review

Do not represent unknown accessibility as
verified accessible.

Use:

- Foreign keys
- Appropriate constraints
- Database migrations
- Geospatial indexes
- Transactional updates
- Proper timestamps

Implement concurrency-safe state changes
for reports and infrastructure updates.

Use SQLAlchemy and Alembic.

Provide reproducible database seeding.

Seed a connected synthetic campus graph
with multiple routing alternatives.

Include:

- Buildings
- Walkways
- Stairs
- Ramps
- Path intersections
- Accessible entrances
- Uneven surfaces
- Blocked pathways

Clearly label all demonstration data.

Do not imply the synthetic map represents
verified Woxsen University infrastructure.


========================================================
09. UI/UX DESIGN PHILOSOPHY
========================================================

Build a premium, modern, polished product.

The application should look like software
developed by an experienced product design team.

NOT a generic dashboard template.

VISUAL PERSONALITY:

- Light
- Clean
- Professional
- Eye-catching
- Trustworthy
- Accessible
- Modern
- Interactive
- Minimal but distinctive

COLOR DIRECTION:

Primary:
Deep teal

Secondary:
Sage green

Background:
Warm white

Accent:
Muted blue

Warning:
Warm amber

Error:
Accessible red

Use semantic design tokens rather than
scattered hardcoded values.

TYPOGRAPHY:

Inter or Plus Jakarta Sans.

ICONS:

Lucide React and purposeful custom SVG elements.

DESIGN RULES:

1. Maintain consistent spacing.
2. Establish strong typography hierarchy.
3. Avoid excessive card nesting.
4. Prioritize readable information.
5. Keep maps visually prominent.
6. Use clear navigation controls.
7. Provide meaningful status indicators.
8. Build consistent components.
9. Use refined borders and subtle shadows.
10. Support keyboard interaction.
11. Respect reduced-motion preferences.
12. Follow WCAG 2.2 AA where practical.

Avoid:

- Generic AI-style gradients everywhere
- Excessive glassmorphism
- Oversized decorative elements
- Overcrowded dashboards
- Unnecessary animations
- Low-contrast text
- Heavy background patterns
- Visually impressive but unusable controls

Use professional design judgment.

Optimize primarily for laptop and desktop use.

Keep essential mobile navigation functional.

Do not waste substantial development time
on unnecessary breakpoint experimentation.


========================================================
10. BRAND IDENTITY
========================================================

APPLICATION:
PathAble

TAGLINE:
Every Path Should Be Possible.

Create a distinctive vector logo.

The logo should combine ideas of:

- Navigation
- Pathways
- Connectivity
- Mobility
- Accessibility
- Inclusion

Avoid using a generic map pin alone.

Create:

- Primary logo
- Compact logo mark
- Application favicon
- Color system
- Typography system
- Icon conventions
- Status indicators
- Route colors
- Map marker conventions

Maintain consistent branding throughout.


========================================================
11. APPLICATION PAGES
========================================================

A. LANDING PAGE

Create a visually polished product homepage.

Include:

- Professional hero section
- Clear value proposition
- Interactive product preview
- Feature explanations
- Navigation demonstration
- How-it-works section
- Accessibility-focused messaging
- Functional calls to action
- Footer

Use subtle animation.

B. NAVIGATION WORKSPACE

This is the primary feature.

Use a map-first layout.

LEFT PANEL:

- Source selection
- Destination selection
- Search
- Accessibility preferences
- Route controls

MAIN AREA:

- Interactive campus map
- Pathway visualization
- Infrastructure markers
- Verified obstacles
- Route overlays

CONTEXTUAL PANEL:

- Route alternatives
- Distance
- Duration
- Accessibility warnings
- Instructions
- Verification information

Implement:

- Animated route drawing
- Route selection
- Route comparison
- Searchable destinations
- Zoom and pan
- Infrastructure details
- Navigation instructions
- Dynamic recalculation

C. ACCESSIBILITY PROFILE

Functional settings:

- Avoid stairs
- Maximum acceptable slope
- Minimum pathway width
- Avoid uneven surfaces
- Wheelchair-related route constraints
- Travel speed preferences

Settings must affect actual calculations.

D. COMMUNITY REPORTING

Features:

- Report obstacle
- Select location
- Choose category
- Upload evidence
- Add description
- Submit report
- View report status
- View report history

E. USER DASHBOARD

Features:

- User profile
- Saved destinations
- Accessibility preferences
- Submitted reports
- Report status updates

F. ADMIN DASHBOARD

Features:

- Infrastructure statistics
- Pending reports
- Verified obstacles
- Infrastructure management
- Accessibility coverage
- Report trends
- Issue resolution tracking
- Review actions
- Audit history

G. AUTHENTICATION

Features:

- Registration
- Login
- Logout
- Protected routes
- Role-based access

Implement loading, empty, error, and success
states throughout the application.


========================================================
12. INTELLIGENT ROUTING ENGINE
========================================================

This is the project's most technically important
component.

Use graph theory.

G = (V, E)

Where:

V = Navigational nodes
E = Walkable pathway connections

Implement:

1. Graph construction
2. Graph validation
3. Dijkstra's Algorithm
4. A* Search
5. Accessibility constraint filtering
6. Weighted path optimization
7. Alternative routes
8. Route reconstruction
9. Dynamic graph updates
10. Unreachable destination handling

ROUTING REQUIREMENTS:

Support personalized restrictions.

Examples:

- Avoid stairs
- Maximum permitted slope
- Minimum acceptable width
- Avoid unsuitable surfaces
- Avoid verified closures

Apply HARD constraints before searching.

Never assign a finite penalty to a prohibited edge
and then allow it to be selected.

For eligible edges, calculate an appropriate
nonnegative routing cost.

Conceptual cost:

Cost(edge) =
    distance_cost
  + slope_penalty
  + surface_penalty
  + uncertainty_penalty

Use consistent units.

Ensure A* uses an admissible and consistent
heuristic under the chosen edge-cost model.

Document assumptions about minimum cost per metre.

Use valid graph connections.

Calculate distance with correct geospatial units.

Do not use raw latitude/longitude differences
as if they were distances in metres.

For routes with unknown accessibility information:

- Apply user-specific policies.
- Communicate uncertainty.
- Avoid declaring the route verified safe.

If a requested route is unavailable:

- Return a structured no-route response.
- Explain the relevant constraints.
- Do not fabricate a route.

API:

POST /api/v1/routes/calculate

INPUT:

- source_id
- destination_id
- accessibility_profile
- selected_algorithm

OUTPUT:

- Route node sequence
- GeoJSON geometry
- Total distance
- Estimated duration
- Accessibility information
- Verification information
- Warnings
- Graph version
- Alternative routes

ALTERNATIVE ROUTES:

Implement meaningful alternatives.

Avoid returning duplicate paths
with slightly different labels.

Test alternatives for validity.

ALGORITHM VALIDATION:

For the same graph, profile, and cost model:

Dijkstra and A* must return equivalent
optimal costs within numerical tolerance.

Test:

- Disconnected graphs
- Invalid nodes
- Closed edges
- Stairs restrictions
- Slope restrictions
- Width restrictions
- Unknown accessibility
- Zero-cost edges where supported
- Competing routes
- Equal-cost routes
- Graph changes

Do not claim optimality without
appropriate algorithmic conditions.


========================================================
13. REAL-TIME INFRASTRUCTURE UPDATES
========================================================

Build a reliable reporting and rerouting pipeline.

WORKFLOW:

User submits obstacle report
            |
            v
Report enters review queue
            |
            v
Administrator verifies report
            |
            v
Database transaction updates status
            |
            v
Affected graph edge becomes unavailable
            |
            v
Graph version increments
            |
            v
Active clients receive update
            |
            v
Affected routes are recalculated

Use Server-Sent Events where appropriate.

Ensure:

- Authorized updates
- Consistent transactions
- Event handling
- Reconnection behavior
- Graph version validation
- Stale information warnings
- Route refresh behavior

Do not trust the frontend as the authority
for infrastructure availability.

The backend and database remain authoritative.

When connectivity fails, do not claim
that navigation data is current.


========================================================
14. AI/ML AND COMPUTER VISION
========================================================

Build a real AI-assisted image analysis system.

Potential classes:

- Stairs
- Pathway obstruction
- Damaged pavement
- Ramp obstruction

IMPORTANT:

Before choosing a model, determine whether
appropriate datasets and pretrained weights exist.

Assess:

- Dataset quality
- License compatibility
- Class definitions
- Label availability
- Class imbalance
- Training requirements
- Computational requirements
- Real-world generalization limitations

Do not assume a standard pretrained model
recognizes specialized accessibility hazards.

Choose object detection or image classification
based on the actual task and available annotations.

If localization is required, prefer a suitable
object detection architecture.

Build a modular ML pipeline.

IMAGE
  |
VALIDATION
  |
PREPROCESSING
  |
MODEL INFERENCE
  |
PREDICTION
  |
ADMINISTRATIVE REVIEW
  |
INFRASTRUCTURE UPDATE

Implement:

- Dataset loading
- Data preprocessing
- Training scripts
- Evaluation scripts
- Inference services
- Model version metadata
- Prediction storage
- Image validation
- Confidence reporting
- Failure handling

SECURITY:

- Limit upload size.
- Validate MIME type and file contents.
- Restrict supported formats.
- Use secure storage.
- Prevent unsafe file handling.

MODEL EVALUATION:

Where an evaluated model exists, report:

- Precision
- Recall
- F1 score
- Confusion matrix
- Relevant detection metrics

Use a held-out evaluation dataset.

Do not fabricate metrics.

Do not claim that a model has been trained
when only training code exists.

If suitable training data or weights
are not available:

1. Complete the ML integration architecture.
2. Implement the training pipeline.
3. Implement the inference interface.
4. Document the missing requirements.
5. Clearly disable unavailable inference.
6. Keep navigation and reporting functional.

Human verification must remain mandatory
before AI suggestions alter official route status.

Never interpret AI confidence as a guarantee
that a pathway is safe.


========================================================
15. REPORTING AND ADMINISTRATIVE WORKFLOW
========================================================

Supported report categories:

- Blocked ramp
- Inaccessible entrance
- Damaged pathway
- Elevator unavailable
- Temporary obstacle
- Other accessibility concern

REPORT LIFECYCLE:

SUBMITTED
    |
PENDING_REVIEW
    |
    +-- VERIFIED
    |
    +-- REJECTED

Verified reports may later become RESOLVED.

Each report should contain:

- Reporter
- Category
- Description
- Location
- Related infrastructure
- Evidence
- Status
- Reviewer
- Review timestamp
- Resolution information

Requirements:

- Persist reports in PostgreSQL.
- Prevent unauthorized modifications.
- Track important state transitions.
- Maintain administrative audit records.
- Prevent conflicting review operations.
- Connect verified reports with infrastructure.

A verified obstruction must have a real effect
on future routing calculations.

Do not treat unreviewed reports as verified facts.


========================================================
16. ADMINISTRATIVE ANALYTICS
========================================================

Build functional database-backed analytics.

Metrics:

- Mapped infrastructure count
- Verified accessible pathways
- Unknown accessibility pathways
- Active verified obstacles
- Pending reports
- Report category distribution
- Resolution trends
- Average resolution time
- Accessibility mapping coverage

Use Recharts.

Create useful filters.

Make charts accessible.

Clearly define how every metric is calculated.

Avoid misleading percentages when the underlying
data is incomplete.

Do not hardcode fake dashboard statistics.

Synthetic seed data is acceptable when
clearly identified as demonstration data.


========================================================
17. SECURITY REQUIREMENTS
========================================================

Implement:

- Secure password hashing
- Authentication
- Role-based authorization
- Protected endpoints
- Input validation
- Safe image uploads
- Rate limiting where appropriate
- Secure configuration
- Environment-based secrets
- Appropriate CORS
- Database transaction integrity
- Minimal sensitive-data collection

Use proper server-side permission checks.

Do not rely only on hiding admin controls
in the frontend.

Implement audit logging for privileged actions.

Do not store unnecessary detailed route histories.

Never commit credentials or secrets.


========================================================
18. TESTING AND VERIFICATION
========================================================

Testing must be part of implementation,
not a final decorative step.

BACKEND:

- Unit tests
- API tests
- Database integration tests
- Authentication tests
- Authorization tests

ALGORITHMS:

- Correctness tests
- Accessibility constraint tests
- No-route tests
- Alternative-route tests
- Graph update tests
- A* versus Dijkstra comparisons

FRONTEND:

- Component tests
- Form tests
- Navigation tests
- API integration tests
- Error-state tests

END-TO-END:

- User registration and login
- Destination selection
- Route calculation
- Accessibility preference changes
- Obstacle submission
- Admin verification
- Dynamic rerouting

MANDATORY CRITICAL TESTS:

TEST A:

The shortest path contains stairs.

A user who cannot use stairs receives
a route without stair-dependent edges.

TEST B:

An accessible pathway is verified blocked.

The original route is invalidated and
a suitable alternative is calculated.

TEST C:

No accessible route exists.

The application displays an honest
unavailable-route result.

TEST D:

A* and Dijkstra agree on the optimal
cost under identical conditions.

TEST E:

An ordinary user cannot approve
infrastructure reports.

TEST F:

An unverified AI prediction does not
automatically block a route.

TEST G:

Unknown accessibility information
is not presented as verified safe.

TEST H:

Database records survive application restart.

TEST I:

Frontend route details correspond
to actual backend results.

TEST J:

Invalid image uploads are rejected safely.

TEST K:

Repeated or conflicting report updates
do not corrupt infrastructure state.

TEST L:

After a graph update, the route cache
does not serve an obsolete route as current.

Execute tests.

Record actual commands and results.

Fix failures.

If tests cannot run, document the blocker.

Never fabricate a successful result.


========================================================
19. PERFORMANCE AND RELIABILITY
========================================================

Prioritize correctness before optimization.

Use:

- Efficient graph structures
- Appropriate indexing
- Reusable components
- Query optimization where justified
- Database transactions
- Clear API contracts
- Structured error handling
- Typed frontend code

Avoid premature complexity.

Introduce caching only when necessary.

If caching routes, invalidate them correctly
when infrastructure changes.

Handle:

- Database outages
- API failures
- Network disconnections
- Invalid route requests
- Unavailable AI inference
- Missing images
- Disconnected graphs

The application should degrade gracefully.


========================================================
20. DEPLOYMENT AND DEVELOPMENT ENVIRONMENT
========================================================

Prepare a reproducible development environment.

Use Docker Compose for PostgreSQL/PostGIS.

Provide:

- Frontend setup
- Backend setup
- Database configuration
- Migration commands
- Seed commands
- Test commands
- Production build commands
- Environment variable examples

Create CI checks for:

- Type checking
- Linting
- Backend tests
- Frontend tests
- Production build

Ensure local development is practical
on a MacBook.

Do not assume paid cloud services.

Do not deploy or push to a remote repository
without explicit authorization.

Prepare the project so GitHub integration
and deployment can happen later.


========================================================
21. PHASE-BY-PHASE IMPLEMENTATION
========================================================

-------------------------------
PHASE 0 — ARCHITECTURE
-------------------------------

MODEL:
GPT-6 Astra

EFFORT:
Extra High

OBJECTIVE:

Create a technically sound foundation.

TASKS:

1. Inspect the workspace.
2. Identify existing project files.
3. Analyze requirements.
4. Compare architecture alternatives.
5. Select suitable technologies.
6. Design database relationships.
7. Define the routing graph.
8. Define API contracts.
9. Establish security requirements.
10. Design the AI subsystem.
11. Define real-time update behavior.
12. Plan frontend architecture.
13. Establish UI/UX design principles.
14. Identify major technical risks.
15. Define acceptance criteria.
16. Create a phase-by-phase implementation plan.
17. Initialize the project structure.

DELIVERABLES:

- ARCHITECTURE.md
- IMPLEMENTATION_PLAN.md
- DATABASE_SCHEMA.md
- API_CONTRACT.md
- ROUTING_DESIGN.md
- MODEL_SWITCH_GUIDE.md
- PROJECT_STATUS.md
- RISK_REGISTER.md
- Initial monorepo structure

DOCUMENT MAJOR DESIGN DECISIONS.

Do not merely propose architecture in chat.

Create actual repository files.

Do not implement Phase 1.

NEXT:

GPT-6.1 Sol — High


-------------------------------
PHASE 1 — BACKEND FOUNDATION
-------------------------------

MODEL:
GPT-6.1 Sol

EFFORT:
High

OBJECTIVE:

Implement a functional backend and database.

TASKS:

1. Configure FastAPI.
2. Configure PostgreSQL/PostGIS.
3. Implement database models.
4. Create migrations.
5. Build authentication.
6. Implement authorization.
7. Create user profile APIs.
8. Implement infrastructure APIs.
9. Implement input validation.
10. Add structured error handling.
11. Seed demonstration data.
12. Write integration tests.
13. Verify database persistence.

ACCEPTANCE:

- Backend starts.
- Database connects.
- Migrations succeed.
- Authentication works.
- Core data persists.
- Tests execute successfully.

NEXT:

GPT-6.1 Sol — High


-------------------------------
PHASE 2 — PREMIUM FRONTEND
-------------------------------

MODEL:
GPT-6.1 Sol

EFFORT:
High

OBJECTIVE:

Build a premium, functional frontend.

TASKS:

1. Establish design tokens.
2. Create brand identity.
3. Implement landing page.
4. Implement authentication screens.
5. Implement dashboard layouts.
6. Create navigation workspace.
7. Integrate React Leaflet.
8. Display demonstration graph geometry.
9. Build location search.
10. Implement accessibility profile controls.
11. Create reporting forms.
12. Create administrative screens.
13. Connect available backend APIs.
14. Add loading/error states.
15. Add polished microinteractions.
16. Test important UI behavior.

For features whose backend phase is not yet complete,
use typed service interfaces and honest unavailable
states rather than fabricated production behavior.

ACCEPTANCE:

- Frontend builds.
- Existing APIs are connected.
- Navigation works.
- Map and infrastructure render.
- Functional controls operate correctly.
- UI is professional and consistent.

NEXT:

GPT-6 Astra — Max


-------------------------------
PHASE 3 — INTELLIGENT ROUTING
-------------------------------

MODEL:
GPT-6 Astra

EFFORT:
Max

OBJECTIVE:

Build the central navigation intelligence.

CRITICAL REASONING PRIORITY:

Ensure graph correctness, accessibility
constraints, and algorithmic optimality.

TASKS:

1. Implement graph construction.
2. Validate graph connectivity.
3. Implement Dijkstra.
4. Implement A*.
5. Design an admissible heuristic.
6. Implement accessibility filtering.
7. Build personalized cost calculations.
8. Implement alternative routes.
9. Implement no-route handling.
10. Create route reconstruction.
11. Implement GeoJSON output.
12. Connect routing APIs.
13. Connect frontend route visualization.
14. Build algorithm comparison tests.
15. Validate route restrictions.
16. Validate graph update handling.
17. Run end-to-end route demonstrations.

ACCEPTANCE:

- Real routing works.
- A* and Dijkstra agree on optimal cost.
- Hard constraints are respected.
- Inaccessible routes are excluded.
- Unreachable destinations are handled.
- Real route geometry appears on the map.
- Alternative routes are meaningful.

NEXT:

GPT-6.1 Sol — High


-------------------------------
PHASE 4 — REPORTING AND LIVE UPDATES
-------------------------------

MODEL:
GPT-6.1 Sol

EFFORT:
High

OBJECTIVE:

Make infrastructure monitoring functional.

TASKS:

1. Implement report submission.
2. Implement evidence uploads.
3. Implement report lifecycle.
4. Implement admin review.
5. Implement verified infrastructure updates.
6. Implement audit records.
7. Introduce graph version changes.
8. Implement Server-Sent Events.
9. Connect route recalculation.
10. Build admin analytics.
11. Connect dashboard charts.
12. Test report-to-routing integration.

ACCEPTANCE:

- Users can submit reports.
- Administrators can review reports.
- Verification changes pathway availability.
- Affected routes recalculate.
- Dashboard metrics reflect real data.

NEXT:

GPT-6 Astra — Extra High


-------------------------------
PHASE 5 — AI/ML INTEGRATION
-------------------------------

MODEL:
GPT-6 Astra

EFFORT:
Extra High

OBJECTIVE:

Implement a technically honest AI-assisted
obstacle recognition subsystem.

TASKS:

1. Evaluate available datasets.
2. Assess model alternatives.
3. Select suitable architecture.
4. Implement preprocessing.
5. Implement dataset loading.
6. Implement training scripts.
7. Implement evaluation scripts.
8. Implement inference services.
9. Integrate model predictions with reports.
10. Add prediction review UI.
11. Test model failure handling.
12. Evaluate available trained models.
13. Document actual performance and limitations.

CRITICAL REQUIREMENT:

Do not claim trained-model functionality
without actual model weights and evidence.

Do not fabricate predictions.

If required resources are unavailable,
complete the integration architecture and
document the precise blocker.

Do not block the functional routing system.

NEXT:

GPT-6 Astra — High


-------------------------------
PHASE 6 — INTEGRATION AND SECURITY
-------------------------------

MODEL:
GPT-6 Astra

EFFORT:
High

OBJECTIVE:

Resolve cross-module defects and improve reliability.

TASKS:

1. Inspect complete application integration.
2. Find incomplete functionality.
3. Execute backend tests.
4. Execute frontend tests.
5. Execute routing tests.
6. Execute end-to-end tests.
7. Review authentication.
8. Review authorization.
9. Review database integrity.
10. Review upload security.
11. Review real-time update behavior.
12. Fix critical defects.
13. Remove unnecessary code.
14. Optimize identified bottlenecks.
15. Verify important UI interactions.

Do not waste time redesigning working components
unless there is a demonstrated problem.

NEXT:

GPT-6.1 Sol — Medium


-------------------------------
PHASE 7 — DEPLOYMENT PREPARATION
-------------------------------

MODEL:
GPT-6.1 Sol

EFFORT:
Medium

OBJECTIVE:

Make the project reproducible and
ready for deployment.

TASKS:

1. Finalize Docker configuration.
2. Verify development setup.
3. Finalize environment templates.
4. Configure CI workflows.
5. Prepare build instructions.
6. Document deployment procedure.
7. Create a professional README.
8. Document architecture.
9. Document algorithms.
10. Document AI limitations.
11. Prepare demo instructions.
12. Prepare GitHub repository structure.

Do not push or deploy without authorization.

ACCEPTANCE:

- Setup instructions work.
- Build commands work.
- CI configuration is valid.
- Documentation reflects the actual code.

NEXT:

GPT-6 Astra — Extra High


-------------------------------
PHASE 8 — FINAL ENGINEERING AUDIT
-------------------------------

MODEL:
GPT-6 Astra

EFFORT:
Extra High

OBJECTIVE:

Conduct an independent, quality-first
assessment of the completed system.

Do not blindly trust previous phase summaries.

Inspect the actual implementation.

AUDIT:

1. Architecture consistency.
2. Frontend functionality.
3. Backend correctness.
4. Database integrity.
5. Graph algorithm correctness.
6. Accessibility restrictions.
7. Dynamic route updates.
8. Administrative permissions.
9. AI integration and limitations.
10. Input validation.
11. Application security.
12. Error handling.
13. Testing coverage.
14. Production build readiness.
15. Deployment documentation.
16. Maintainability.
17. Performance.
18. UI consistency.
19. Accessibility.
20. Remaining incomplete functionality.

Run relevant verification commands.

Investigate failures rather than hiding them.

Fix critical defects where feasible.

Document unresolved limitations.

Provide a final technical report with:

- Implemented features
- Architecture summary
- Algorithm summary
- AI implementation status
- Test evidence
- Security findings
- Known limitations
- Deployment readiness
- Recommended future improvements

Do not declare the system production-ready
unless the evidence supports that conclusion.


========================================================
22. ENGINEERING QUALITY GATES
========================================================

Every phase must meet defined acceptance criteria.

Before declaring completion:

1. Confirm the implemented functionality.
2. Inspect modified files.
3. Check interfaces and dependencies.
4. Run relevant tests.
5. Verify no regressions in affected modules.
6. Identify unresolved risks.
7. Update PROJECT_STATUS.md.
8. Record exact test results.
9. Record the next phase and model.
10. Stop execution.

Do not continue simply because the phase
appears visually complete.

Do not confuse code generation with
successful implementation.

When a failure is identified:

- Reproduce it.
- Identify the cause.
- Apply a focused fix.
- Retest.
- Record the outcome.

Do not perform broad rewrites without
a technical justification.


========================================================
23. EFFICIENT DEVELOPMENT RULES
========================================================

Use the available models intelligently.

GPT-6 ASTRA:

Use for:
- Architecture decisions
- Complex algorithm design
- AI/ML decisions
- Difficult cross-module debugging
- Security review
- Final engineering audit

GPT-6.1 SOL:

Use for:
- Backend implementation
- Frontend implementation
- UI/UX development
- API integration
- Database operations
- Reporting systems
- Dashboard development
- Deployment preparation

GPT-6 LUNA:

Optional for:
- Small isolated documentation tasks
- Simple formatting
- Straightforward repetitive changes

Do not use high reasoning effort unnecessarily.

Do not repeatedly regenerate existing files.

Do not make cosmetic changes that introduce
new regressions.

Do not spend excessive time polishing
minor animations while critical functionality
remains incomplete.

Do not compromise correctness or security
to save tokens.

Do not introduce complicated technology
without a genuine engineering benefit.


========================================================
24. DOCUMENTATION AND CONTINUITY
========================================================

Maintain persistent project documentation.

Required files:

README.md

docs/ARCHITECTURE.md

docs/IMPLEMENTATION_PLAN.md

docs/DATABASE_SCHEMA.md

docs/API_CONTRACT.md

docs/ROUTING_DESIGN.md

docs/MODEL_SWITCH_GUIDE.md

docs/PROJECT_STATUS.md

docs/RISK_REGISTER.md

docs/TESTING.md

docs/DEPLOYMENT.md

Document major architectural decisions using
concise Architecture Decision Records.

Before starting any phase:

1. Inspect relevant repository files.
2. Read PROJECT_STATUS.md.
3. Read the relevant implementation plan.
4. Identify completed functionality.
5. Identify pending functionality.
6. Preserve existing architectural contracts.

Never assume previous work was completed
merely because documentation says so.

Verify important dependencies through the code.

At phase boundaries, update documentation
so development can continue reliably
after a model switch or a new Codex session.


========================================================
25. REQUIRED PHASE COMPLETION FORMAT
========================================================

At the end of EVERY phase, display:

=============================================
PATHABLE — DEVELOPMENT PHASE COMPLETED
=============================================

COMPLETED PHASE:
[Phase number and name]

MODEL USED:
[Exact model]

REASONING EFFORT:
[Exact effort]

IMPLEMENTATION STATUS:
[Completed / Partially completed / Blocked]

WORK COMPLETED:
[Concise summary]

IMPORTANT FILES MODIFIED:
[List of relevant files]

FUNCTIONALITY VERIFIED:
[Actual working features]

TESTS EXECUTED:
[Exact commands and real results]

KNOWN ISSUES:
[Outstanding problems]

NEXT PHASE:
[Phase number and name]

RECOMMENDED MODEL:
[Exact model name]

RECOMMENDED REASONING EFFORT:
[Exact effort]

MODEL SWITCH REQUIRED:
[YES / NO]

REQUIRED USER ACTION:
[Exact instructions]

CONTINUATION PROMPT:
[Short prompt to continue]

STATUS:
AWAITING USER AUTHORIZATION

=============================================

Do not claim a phase passed verification
unless the relevant checks actually ran.

If the phase is blocked, explain the problem
and recommend a specific resolution.

If the next phase requires another model,
tell me exactly which model to select.

If the next phase requires different reasoning
effort, tell me exactly which effort to select.

Do not automatically continue.

Wait for authorization.


========================================================
26. FINAL PROJECT SUCCESS CRITERIA
========================================================

PathAble must demonstrate:

1. Functional authentication.
2. Real PostgreSQL/PostGIS persistence.
3. A professional and interactive frontend.
4. Functional campus mapping.
5. Real Dijkstra implementation.
6. Real A* implementation.
7. Accessibility-aware route constraints.
8. Alternative route generation.
9. Accurate route visualization.
10. Valid obstacle reporting.
11. Administrative verification.
12. Dynamic infrastructure updates.
13. Real route recalculation.
14. Functional database-backed analytics.
15. AI integration with honestly reported status.
16. Secure API access.
17. Reliable error handling.
18. Automated tests.
19. Reproducible development environment.
20. Professional project documentation.

The product should be suitable for a live
technical demonstration.

When a feature is incomplete, report it honestly.

Do not conceal unfinished functionality.


========================================================
27. START EXECUTION
========================================================

CURRENT AUTHORIZED MODEL:

GPT-6 Astra

REASONING EFFORT:

Extra High

CURRENT PHASE:

PHASE 0 — ARCHITECTURE AND CRITICAL DESIGN

START NOW.

Your immediate responsibilities:

1. Inspect the current workspace.

2. Understand the entire project specification.

3. Identify technical challenges and risks.

4. Evaluate suitable architectural alternatives.

5. Design the complete system architecture.

6. Design the database schema.

7. Define the graph and routing model.

8. Establish correctness requirements
   for A* and Dijkstra.

9. Define accessibility data policies.

10. Define all major API contracts.

11. Design authentication and permissions.

12. Design the reporting lifecycle.

13. Design infrastructure update handling.

14. Establish the AI/ML implementation strategy.

15. Define the frontend design system.

16. Establish project folder structure.

17. Create the architecture documents.

18. Create the implementation plan.

19. Create the risk register.

20. Create MODEL_SWITCH_GUIDE.md.

21. Create PROJECT_STATUS.md.

22. Define acceptance criteria for all phases.

23. Establish initial testing conventions.

IMPORTANT:

Create actual files in the repository.

Do not merely explain what should be built.

Do not begin Phase 1.

When Phase 0 is complete, stop and report:

"PHASE 0 COMPLETE.

NEXT REQUIRED MODEL:
GPT-6.1 Sol

REASONING EFFORT:
High

Please switch to GPT-6.1 Sol with High
reasoning effort.

Then send:

Continue PathAble Phase 1.
Implement the backend and database foundation
according to the approved architecture.
Run all relevant tests and stop at the next
phase boundary."

WAIT FOR MY AUTHORIZATION.

BEGIN PHASE 0.
