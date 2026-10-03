# Road Intelligence & Pothole Management Platform

An end-to-end, multi-tenant road infrastructure intelligence and pothole management platform. The platform collects road condition data, runs a damage-detection pipeline (a YOLO11s model trained on RDD2022 India for cracks and potholes; a rule-based OpenCV heuristic fallback is used only when no trained weights are configured), associates findings with road segments in PostGIS, produces rule-based health and deterioration estimates, manages maintenance, and records repair evidence for human verification. See section 4 for what is actually implemented.

---

## 1. System Architecture

```text
                     +-----------------------------+
                     |    Web & Android Clients    |
                     +--------------+--------------+
                                    | HTTPS
                                    v
                     +-----------------------------+
                     |     Nginx Reverse Proxy     |
                     +--------------+--------------+
                                    |
                                    v
                     +-----------------------------+
                     |    FastAPI Backend API      |
                     +-------+---------------+-----+
                             |               |
               +-------------+               +-------------+
               v                                           v
      +------------------+                       +------------------+
      |  PostgreSQL/     |                       |  Redis Broker    |
      |  PostGIS (DB)    |                       |  & Celery Queue  |
      +------------------+                       +--------+---------+
               ^                                          |
               |                                          v
               |                                 +------------------+
               +---------------------------------+  AI Worker       |
                                                 |  (YOLO path +    |
                                                 |  OpenCV fallback)|
                                                 +------------------+
```

---

## 2. Monorepo Structure

```text
├── apps/
│   ├── web/               # Next.js 14+ Web Application (TypeScript, Tailwind, Leaflet)
│   └── android/           # Android Field Inspection App (Kotlin, Jetpack Compose, Room)
├── services/
│   ├── api/               # FastAPI Backend Service (SQLAlchemy 2.0, Alembic, Pydantic v2)
│   └── ai-worker/         # Detection worker (Ultralytics YOLO path, OpenCV heuristic fallback, Celery)
├── packages/
│   └── shared/            # Shared schema definitions and constants
├── infrastructure/
│   ├── docker/            # Service Dockerfiles and build configs
│   ├── nginx/             # Nginx reverse proxy configuration
│   └── scripts/           # Automation and deployment scripts
├── docs/                  # 16 Authoritative Specification Documents
├── data/                  # Local data storage and AI model artifacts
├── docker-compose.yml     # Multi-service local and VPS orchestrator
├── .env.example           # Canonical environment configuration template
└── README.md
```

---

## 3. Quick Start (Development)

### Prerequisites

- Python 3.11+ / 3.12+
- Node.js 18+ & npm
- Docker & Docker Compose
- PostgreSQL 16 with PostGIS extension (or run via Docker)

### Run Services via Docker Compose

```bash
cp .env.example .env
docker compose up -d
```

Access services:
- **Web Application**: http://localhost:3000
- **FastAPI API & Docs**: http://localhost:8000/docs
- **Nginx Entrypoint**: http://localhost/

---

## 4. Platform Implementation Status & Roadmap Milestones

Status reflects the code as it currently runs, not the target design in the specification documents.
**Implemented** = works end to end; **Partial** = works with stated limits; **Rule-based** = deterministic
formulas, not trained ML; **Not implemented** = absent.

| Area | Status | Notes |
|---|---|---|
| Backend foundation, PostGIS schema, Alembic | Implemented | Verified on PostgreSQL 16 / PostGIS 3.4 (integration tests) |
| Authentication, organization isolation | Implemented | JWT + permissions; only the administrator role is seeded by `app.bootstrap` |
| Roads, segments, inspections, signed media upload | Implemented | Local signed storage verified; Supabase tested against a mocked API only |
| Android field app | Implemented | Photo capture, GPS, runtime permissions, sync and upload verified on a physical Android 15 device; no video capture |
| AI processing pipeline (Celery + Redis) | Implemented | Dispatch, retries and result storage verified end to end |
| Damage detection model | Implemented, Partial | YOLO11s fine-tuned on RDD2022 India (`rdd2022-india-yolo11s` / `india-v1`); detects cracks (D00/D10/D20 → CRACK) and potholes (D40 → POTHOLE) only, not depressions, waterlogging or surface damage. Held-out RDD2022 India test split: mAP50 0.326, mAP50-95 0.134 (transverse cracks D10 effectively undetected). Not validated on Pune roads or other cities. Scores are uncalibrated model confidence. Weights are not in git; see `services/ai-worker/training/README.md`. The OpenCV heuristic fallback (rule-based, not a trained model) is used only when no trained weights are configured and is labelled as such |
| Severity assessment | Rule-based | Bounding-box size and damage class only |
| Damage area | Not implemented | Physical area is not estimated without camera calibration (field left empty) |
| Human damage review | Implemented | |
| Road health score (0-100) | Rule-based, Partial | Severity-weighted deductions; computed only when its endpoint is called; no traffic factor |
| Deterioration prediction | Rule-based | Hand-weighted rules (`Rule-Based-Deterioration-Estimate`), no trained model, no confidence/uncertainty; no weather or traffic data |
| Maintenance jobs, assignment, status machine | Implemented | No scheduling optimisation |
| Repair verification | Partial | Evidence upload API + human VERIFIED/REJECTED decision. Automated check covers evidence presence and GPS distance only; no before/after image comparison yet |
| Recurrence tracking | Rule-based, Partial | Distance (30 m) + time matching; run only when its endpoint is called; no escalation |
| Web dashboard, inspection detail, GIS map | Implemented | No charts; prediction and health are not yet shown |
| Reports | Partial | JSON reports only (no PDF/CSV) |
| Production deployment | Not implemented | No TLS/secret management/monitoring; CI workflow defined but not yet run |

---

## 5. Automated Verification & Testing

The platform includes a comprehensive test suite covering all operational modules:

- **Pytest Backend Suite:** **105 Passed, 0 Failed (100% Pass Rate)**
- **Next.js Web Build:** **15 Static Routes compiled with 0 TypeScript/ESLint errors**
- **Android Lint & Compilation:** Clean architecture (Domain / Data / Presentation) with Room & WorkManager

```bash
# Execute complete backend integration suite
pytest services/api/tests/

# Build production web application
cd apps/web && npm run build
```

---

## 6. Authoritative Documentation

All 16 authoritative specifications reside in the `docs/` directory:
- `01_PROJECT_CONTEXT.md` — Project context and business objectives
- `02_PRD.md` — Product requirements document
- `03_SRS.md` — Software requirements specification
- `04_SYSTEM_ARCHITECTURE.md` — End-to-end system architecture
- `05_TECH_STACK.md` — Technology selection and dependency lockdown
- `06_DATABASE_SCHEMA.md` — PostgreSQL 16 & PostGIS physical schema
- `07_API_SPECIFICATION.md` — Authoritative REST API contracts
- `08_AI_ML_SPECIFICATION.md` — Target AI/ML design (YOLOv8 detection, XGBoost deterioration); see its implementation-status note
- `09_USER_ROLES_PERMISSIONS.md` — RBAC matrix and security boundaries
- `10_UI_UX_SPECIFICATION.md` — Design system and dark mode interface guidelines
- `11_ANDROID_APP_SPEC.md` — Android architecture and offline-first sync engine
- `12_SECURITY.md` — Platform security, encryption, and audit controls
- `13_DEPLOYMENT.md` — Production deployment and container orchestration
- `14_TESTING_STRATEGY.md` — Verification standards and coverage requirements
- `15_ROADMAP.md` — Master implementation roadmap and execution phases
- `16_CHANGELOG.md` — Architecture changelog and version history
