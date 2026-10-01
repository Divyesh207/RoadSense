# Road Intelligence & Pothole Management Platform

An end-to-end, multi-tenant road infrastructure intelligence and pothole management platform. The platform collects road condition data, detects and classifies damage using local AI/ML models, associates findings with road segments in PostGIS, predicts deterioration, prioritizes maintenance, and verifies repairs using before/after evidence.

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
                                                 |  (YOLO/PyTorch/  |
                                                 |   XGBoost)       |
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
│   └── ai-worker/         # Local AI Inference Service (YOLOv8, PyTorch, OpenCV, XGBoost)
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

## 4. Documentation

All 16 authoritative specifications reside in the `docs/` directory:
- `01_PROJECT_CONTEXT.md`
- `02_PRD.md`
- `03_SRS.md`
- `04_SYSTEM_ARCHITECTURE.md`
- `05_TECH_STACK.md`
- `06_DATABASE_SCHEMA.md`
- `07_API_SPECIFICATION.md`
- `08_AI_ML_SPECIFICATION.md`
- `09_USER_ROLES_PERMISSIONS.md`
- `10_UI_UX_SPECIFICATION.md`
- `11_ANDROID_APP_SPEC.md`
- `12_SECURITY.md`
- `13_DEPLOYMENT.md`
- `14_TESTING_STRATEGY.md`
- `15_ROADMAP.md`
- `16_CHANGELOG.md`
