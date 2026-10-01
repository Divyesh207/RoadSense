# TECH_STACK.md

# Road Intelligence & Pothole Management Platform

**Document Type:** Technology Stack & Engineering Standards  
**Version:** 1.0  
**Status:** Approved Technology Baseline  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`, `SRS.md`, `SYSTEM_ARCHITECTURE.md`  
**Last Updated:** October 2026

---

# 1. Purpose

This document defines the approved technology stack for the Road Intelligence & Pothole Management Platform.

Its purpose is to prevent coding agents and developers from independently selecting incompatible frameworks, libraries, infrastructure, or architectural patterns.

Unless explicitly changed through the architecture-change process, implementation should follow this document.

---

# 2. Technology Philosophy

The platform prioritizes:

- Production reliability
- Strong typing
- Maintainability
- Local AI/ML execution
- API-first architecture
- Open-source technologies where practical
- PostgreSQL
- Modular services
- Containerized deployment
- Explainable intelligence
- Offline field operation
- Future GPU scalability

The platform should avoid unnecessary technology complexity.

---

# 3. Technology Stack Summary

| Layer | Technology |
|---|---|
| Web | Next.js |
| Web Language | TypeScript |
| Web Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Web Animation | Framer Motion |
| Charts | Recharts |
| Maps | Leaflet + OpenStreetMap |
| Backend | FastAPI |
| Backend Language | Python |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Database | PostgreSQL |
| Managed Database | Supabase PostgreSQL |
| Geospatial | PostGIS |
| Authentication | JWT |
| Password Hashing | bcrypt |
| AI Detection | YOLO + PyTorch |
| Computer Vision | OpenCV |
| ML Prediction | XGBoost |
| ML Utilities | scikit-learn |
| Data Processing | Pandas |
| Numerical Processing | NumPy |
| Job Queue | Redis |
| Task Processing | Celery |
| Object Storage | Supabase Storage |
| Android | Kotlin |
| Android UI | Jetpack Compose |
| Android Background Sync | WorkManager |
| Reverse Proxy | Nginx |
| Containers | Docker |
| Orchestration | Docker Compose |
| Web Deployment | Vercel |
| Backend Deployment | VPS |
| Database/Storage Deployment | Supabase |
| API Documentation | OpenAPI / FastAPI |
| Testing — Python | Pytest |
| Testing — Web | Vitest + Playwright |
| Android Testing | JUnit + AndroidX testing |
| Version Control | Git + GitHub |
| CI/CD | GitHub Actions |

---

# 4. Technology Selection Rules

## TS-001

Do not introduce a new framework when an approved technology already solves the requirement.

## TS-002

Do not replace PostgreSQL with another production database.

## TS-003

Do not replace FastAPI with another backend framework.

## TS-004

Do not introduce an external generative-AI API into the core AI pipeline.

## TS-005

Do not introduce MongoDB, Firebase, or another primary database.

## TS-006

Do not allow frontend applications to connect directly to PostgreSQL.

## TS-007

Do not add microservices unnecessarily.

## TS-008

Long-running AI work must remain asynchronous.

## TS-009

Dependencies must be pinned or constrained to compatible versions.

## TS-010

Security-sensitive dependencies must be maintained and periodically updated.

---

# 5. Web Stack

## 5.1 Framework

**Next.js**

Responsibilities:

- Web application
- Routing
- Server-side rendering where useful
- Protected application routes
- Static optimization
- Production frontend build

The application should use the modern App Router architecture.

---

# 6. Web Language

**TypeScript**

TypeScript should be used throughout the web application.

Strict type checking should be enabled.

Recommended configuration:

```text
strict: true
```

Avoid:

```typescript
any
```

unless there is a documented technical reason.

---

# 7. React

Next.js will use React as its UI framework.

React components should be divided into:

```text
Server Components
Client Components
```

Client Components should be used only where browser-side interactivity is required.

Examples:

- Interactive maps
- Camera/media UI
- Forms
- Charts
- Animations
- Interactive filters

---

# 8. Styling

**Tailwind CSS**

Tailwind should be the primary styling system.

Do not introduce another global styling framework unless explicitly approved.

---

# 9. UI Components

**shadcn/ui**

shadcn/ui will provide reusable UI primitives.

Components should be customized to match the platform design system.

Expected primitives include:

- Button
- Input
- Select
- Dialog
- Dropdown
- Tabs
- Card
- Table
- Badge
- Tooltip
- Toast
- Sheet
- Form components

---

# 10. Animation

**Framer Motion**

Use for meaningful interface motion:

- Page transitions
- Dialog animation
- Card transitions
- Loading states
- Expand/collapse
- Dashboard interactions

Avoid excessive animation that harms usability.

---

# 11. Charts

**Recharts**

Used for:

- Road-health trends
- Damage statistics
- Severity distributions
- Maintenance metrics
- Prediction visualizations
- Inspection analytics

Charts must remain responsive.

---

# 12. Mapping

**Leaflet**

Used for:

- Road maps
- Damage markers
- Road segments
- Maintenance locations
- Inspection locations
- Geographic filtering

---

# 13. Basemap

**OpenStreetMap**

OpenStreetMap will be used as the initial map/basemap source.

The application must respect the applicable OpenStreetMap tile usage and attribution requirements.

The map layer is not the authoritative application database.

---

# 14. GIS Data

The application's road geometry belongs to the platform's PostgreSQL/PostGIS database.

OpenStreetMap is primarily used for map visualization and geographic reference.

Architecture:

```text
OpenStreetMap
      ↓
Basemap / Geographic Context

Application PostGIS
      ↓
Authoritative Road Geometry
      ↓
Damage / Inspection / Maintenance Association
```

---

# 15. Backend Framework

**FastAPI**

FastAPI is the sole primary backend API framework.

Responsibilities:

- REST APIs
- Authentication
- Authorization
- Validation
- Business workflows
- Database operations
- Job creation
- File-upload authorization
- Analytics
- Reporting
- Audit logging

---

# 16. Python

The backend and AI stack will use Python.

Recommended baseline:

```text
Python 3.12+
```

The exact production minor version must be pinned consistently across development, CI, and deployment.

Do not mix multiple Python runtime versions between API and worker without an explicit reason.

---

# 17. API Validation

**Pydantic**

Pydantic models are used for:

- Request validation
- Response schemas
- Configuration
- Internal DTO validation
- Structured AI result validation

FastAPI's native Pydantic integration should be used.

---

# 18. ORM

**SQLAlchemy 2.x**

SQLAlchemy will be used for database access.

Use modern SQLAlchemy patterns.

Avoid raw SQL except where:

- Performance requires it
- PostgreSQL/PostGIS functionality is not practical through ORM
- A migration requires it

Raw SQL must remain parameterized.

---

# 19. Database Driver

Use a PostgreSQL-compatible Python driver appropriate for SQLAlchemy 2.x.

The exact driver should be standardized in the backend dependency file and used consistently across the API and migration tooling.

Do not mix multiple PostgreSQL drivers without justification.

---

# 20. Database

**PostgreSQL**

PostgreSQL is the authoritative production database.

It stores:

- Users
- Organizations
- Roads
- Road segments
- Inspections
- Media metadata
- Damage
- AI results
- Road health
- Predictions
- Maintenance
- Repairs
- Verification
- Recurrence
- Notifications
- Audit records

---

# 21. Managed PostgreSQL

**Supabase PostgreSQL**

Supabase is the initial managed PostgreSQL provider.

The application architecture must continue to treat PostgreSQL as PostgreSQL.

The business layer must not become dependent on Supabase-specific client-side database APIs.

---

# 22. Geospatial Database

**PostGIS**

PostGIS should be enabled in the selected Supabase PostgreSQL project.

Used for:

- Point coordinates
- Road geometry
- Segment geometry
- Spatial queries
- Distance calculations
- Bounding-box searches
- Damage-to-road association
- Recurrence location matching

---

# 23. Database Migration

Database schema changes must be managed through version-controlled migrations.

Preferred tooling:

**Alembic**

Architecture:

```text
SQLAlchemy Models
       ↓
Alembic Migration
       ↓
PostgreSQL
```

Do not manually alter production tables without a corresponding migration.

---

# 24. Authentication

Authentication will be implemented by the FastAPI backend.

Primary mechanism:

**JWT**

JWTs identify authenticated users.

The backend remains responsible for validating:

- Signature
- Expiration
- User identity
- Organization scope
- Required claims

---

# 25. Password Security

Passwords must never be stored in plaintext.

Use:

**bcrypt**

Recommended password policy should be defined in `SECURITY.md`.

---

# 26. Authorization

Authorization uses:

```text
RBAC
+
Organization Scope
+
Resource-Level Access
```

Roles:

```text
ADMINISTRATOR
AUTHORITY
INSPECTOR
CONTRACTOR
```

The exact permission matrix is defined in:

```text
09_USER_ROLES_PERMISSIONS.md
```

---

# 27. AI Framework

## Primary AI framework

**PyTorch**

Used as the underlying deep-learning framework.

---

# 28. Object Detection

**YOLO**

YOLO is the primary road-damage detection architecture.

It will be used for detecting classes such as:

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

The exact model variant is a model-development decision and must be documented with the model version.

---

# 29. Computer Vision

**OpenCV**

OpenCV will be used for:

- Image preprocessing
- Image transformations
- Frame processing
- Computer-vision utilities
- Image quality checks
- Video processing support

---

# 30. Video Processing

Where required, the AI worker may use:

**FFmpeg**

Responsibilities:

- Video decoding
- Frame extraction
- Format conversion
- Video metadata inspection

FFmpeg should remain inside the AI/processing environment.

---

# 31. Classical Machine Learning

**XGBoost**

XGBoost will be used for road deterioration prediction and other tabular ML tasks where appropriate.

Example:

```text
Historical Road Features
        ↓
Feature Engineering
        ↓
XGBoost
        ↓
Deterioration Prediction
```

---

# 32. Machine Learning Utilities

**scikit-learn**

Used for:

- Dataset splitting
- Evaluation metrics
- Preprocessing
- Feature utilities
- Baseline models
- Validation pipelines

scikit-learn should not be used as a replacement for YOLO detection.

---

# 33. Data Processing

**Pandas**

Used for:

- Historical datasets
- Feature engineering
- Analytics preparation
- Model training data
- Evaluation datasets

Pandas should primarily be used in processing/training workflows rather than unnecessarily inside every API request.

---

# 34. Numerical Processing

**NumPy**

Used for:

- Numerical transformations
- Model inputs
- Image/data arrays
- Mathematical operations

---

# 35. AI Model Storage

AI model artifacts should not be committed directly into the Git repository unless they are intentionally tiny and explicitly approved.

Recommended architecture:

```text
Git
 ↓
Model Metadata / Configuration

Object Storage / Model Registry
 ↓
Model Artifact
```

Production workers load an explicitly configured model version.

---

# 36. Model Versioning

Every production AI model must have:

```text
Model Name
Model Version
Artifact Identifier
Training Dataset Version
Configuration Version
Deployment Status
```

Example:

```text
road-damage-detector
v1.0.0
```

---

# 37. AI Result Reproducibility

AI processing should record sufficient metadata to reproduce or investigate a result.

Where applicable:

```text
model_version
configuration_version
processing_timestamp
input_media_id
confidence_threshold
worker_version
```

---

# 38. Job Queue

**Redis**

Redis is used primarily as:

- Task broker
- Temporary queue infrastructure
- Optional cache

Redis is not the authoritative business database.

---

# 39. Task Processing

**Celery**

Celery will process long-running background jobs.

Typical tasks:

```text
process_inspection
run_damage_detection
process_video
calculate_prediction
verify_repair
generate_report
calculate_recurrence
```

---

# 40. Job Architecture

```text
FastAPI
   ↓
Celery Task
   ↓
Redis
   ↓
Celery Worker
   ↓
PostgreSQL
```

The API should return a job identifier for operations that do not complete quickly.

---

# 41. Object Storage

**Supabase Storage**

Used for:

- Inspection images
- Inspection videos
- Repair evidence
- Generated reports
- AI-related media artifacts

PostgreSQL stores object metadata and references.

---

# 42. Storage Bucket Strategy

Logical private buckets may include:

```text
inspection-media
repair-evidence
reports
model-artifacts
```

Exact bucket names are implementation configuration and should be centralized.

Buckets should not automatically be public.

---

# 43. Storage Access

Clients should receive short-lived authorized access rather than permanent storage credentials.

Preferred pattern:

```text
Client
 ↓
FastAPI
 ↓
Authorization
 ↓
Signed Upload/Download URL
 ↓
Storage
```

---

# 44. Android Technology

Android application:

**Kotlin**

Minimum/target Android versions will be finalized during Android implementation based on supported device requirements.

The application should target modern Android APIs while maintaining practical compatibility for field devices.

---

# 45. Android UI

**Jetpack Compose**

Compose is the primary UI toolkit.

Use:

- Composable screens
- State-driven UI
- ViewModels
- Material components
- Navigation

---

# 46. Android Architecture

The Android application should follow:

```text
Presentation
     ↓
Domain
     ↓
Data
```

With repositories separating local and remote sources.

---

# 47. Android Camera

Use Android's modern camera APIs, preferably:

**CameraX**

Camera functionality includes:

- Photo capture
- Video capture where required
- Camera preview
- Capture metadata
- Basic image validation

---

# 48. Android Location

Use Android location APIs through a suitable location provider.

Required information may include:

```text
latitude
longitude
accuracy
timestamp
```

Location permission must be explicitly requested and handled.

---

# 49. Android Offline Processing

Offline inspections require local persistence.

The implementation should use:

**Room**

Room will provide structured local persistence for:

- Draft inspections
- Media metadata
- Upload queue
- Synchronization state
- Retry metadata

---

# 50. Android Background Synchronization

Use:

**WorkManager**

WorkManager handles:

- Upload retry
- Synchronization
- Background processing
- Connectivity-aware work

Example:

```text
Local Queue
    ↓
WorkManager
    ↓
Network Available?
    ↓
Upload
    ↓
Confirm
```

---

# 51. Android Networking

Use a standard typed HTTP client such as:

**Retrofit + OkHttp**

Responsibilities:

- API communication
- Authentication headers
- Timeouts
- Retry handling where appropriate
- Error parsing

The exact API contract comes from FastAPI/OpenAPI.

---

# 52. Android Serialization

Use:

**Kotlinx Serialization**

for structured API/local data where practical.

The serialization models must follow the backend API contract.

---

# 53. Web Testing

## Unit Testing

**Vitest**

Use for:

- Utility functions
- Feature logic
- Data transformations
- Validation helpers

## End-to-End Testing

**Playwright**

Use for:

- Login
- Dashboard
- Inspection workflows
- Maintenance workflows
- Critical user journeys

---

# 54. Backend Testing

**Pytest**

Use for:

- Unit tests
- Service tests
- Repository tests
- API tests
- Integration tests
- AI pipeline tests

---

# 55. API Testing

FastAPI endpoints should be tested with an HTTP test client.

Tests must cover:

```text
200
201
400
401
403
404
409
422
500
```

where applicable.

---

# 56. Database Testing

Database integration tests should run against an isolated test database.

Do not execute tests against production.

---

# 57. AI Testing

AI testing must include:

### Unit tests

For:

- Preprocessing
- Postprocessing
- Severity calculations
- Feature generation

### Model tests

For:

- Detection outputs
- Confidence thresholds
- Expected class behavior

### Regression tests

To detect unexpected changes between model versions.

---

# 58. Android Testing

Use:

- JUnit
- AndroidX testing
- Compose UI testing

Important scenarios:

```text
Login
Camera permission
Location permission
Inspection creation
Offline queue
Retry
Upload
Sync
Error handling
```

---

# 59. API Documentation

FastAPI's OpenAPI generation will be the canonical API contract source.

The API specification document should supplement the generated OpenAPI documentation with:

- Business meaning
- Workflow rules
- State transitions
- Authentication
- Examples
- Error semantics

---

# 60. API Versioning

Initial API version:

```text
/api/v1/
```

Future breaking changes should use a new API version rather than silently changing existing contracts.

---

# 61. Reverse Proxy

**Nginx**

Nginx is used on the VPS for:

- TLS termination
- Reverse proxy
- Request routing
- Connection management
- Basic security controls

---

# 62. Containerization

**Docker**

The following application components should be containerized:

```text
FastAPI
AI Worker
Redis
Nginx
```

The frontend remains deployed through Vercel.

Android is distributed as an application package rather than as a container.

---

# 63. Container Orchestration

**Docker Compose**

Docker Compose is the initial production orchestration mechanism.

It provides:

- Service definitions
- Networking
- Environment configuration
- Restart policies
- Dependency relationships
- Local reproducibility

Kubernetes is not required for the initial deployment.

---

# 64. VPS Architecture

Initial backend deployment:

```text
VPS
│
├── Nginx
├── FastAPI
├── Celery Worker
└── Redis
```

External:

```text
Supabase PostgreSQL
Supabase Storage
Vercel
```

---

# 65. Future Infrastructure Scaling

When workload increases:

```text
Initial VPS
    ↓
Separate AI Worker
    ↓
Dedicated GPU Server
    ↓
Multiple AI Workers
    ↓
Load-balanced API
```

The application should not require a complete rewrite.

---

# 66. Frontend Deployment

**Vercel**

Vercel is the preferred initial deployment platform for the Next.js web application.

Production web configuration must point to the production FastAPI API URL.

---

# 67. Backend Deployment

FastAPI and Celery run on the VPS using Docker Compose.

Recommended production flow:

```text
GitHub
   ↓
CI
   ↓
Build
   ↓
Test
   ↓
Docker Image
   ↓
Deployment
   ↓
VPS
```

---

# 68. CI/CD

**GitHub Actions**

CI should validate:

```text
Web
 ├── TypeScript
 ├── Lint
 ├── Unit Tests
 └── Build

Backend
 ├── Formatting
 ├── Lint
 ├── Type Checking
 └── Pytest

AI Worker
 ├── Lint
 ├── Tests
 └── Build
```

Deployment workflows should require successful validation.

---

# 69. Code Quality

Recommended tools:

### Python

- Ruff
- Black-compatible formatting where required
- Pytest
- MyPy where useful

### TypeScript

- ESLint
- Prettier
- TypeScript compiler

### Android

- Kotlin formatting/lint
- Android Lint

The exact formatter configuration must be standardized in the repository.

---

# 70. Environment Management

Use:

```text
.env
.env.example
```

Production secrets must never be committed.

Examples:

```text
DATABASE_URL
JWT_SECRET
REDIS_URL
STORAGE_SECRET
AI_MODEL_PATH
```

---

# 71. Secret Management

Secrets must be provided through:

- Local environment variables during development
- Vercel environment variables for web
- VPS environment/secrets for backend
- GitHub Actions secrets for CI/CD

Never:

```text
commit secret
hard-code secret
print secret in logs
send secret to client
```

---

# 72. Logging

Use structured logging.

Recommended format:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "api",
  "request_id": "...",
  "message": "Inspection created"
}
```

AI workers should include:

```text
job_id
inspection_id
model_version
worker_id
```

where relevant.

---

# 73. Error Handling

The backend uses a consistent structured error response.

Example:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": {},
    "request_id": "..."
  }
}
```

The exact error taxonomy belongs to `API_SPECIFICATION.md`.

---

# 74. Dependency Management

## Python

Use:

```text
pyproject.toml
```

with locked/controlled dependency versions.

## Web

Use:

```text
package.json
```

and lockfile.

## Android

Use Gradle version catalogs where practical.

---

# 75. Local Development

Developers should be able to start the main infrastructure with:

```text
Docker Compose
```

Typical local services:

```text
PostgreSQL or Supabase development database
Redis
FastAPI
AI Worker
Web
```

If using hosted Supabase during development, credentials must be environment-specific.

---

# 76. Local AI Development

Developers without GPU access should be able to run the AI pipeline in CPU mode for functional testing.

Performance will not be equivalent to GPU inference.

The system should expose configuration such as:

```text
AI_DEVICE=cpu
```

or equivalent.

---

# 77. Production AI

Production AI configuration may use:

```text
AI_DEVICE=cpu
```

initially.

When GPU infrastructure becomes available:

```text
AI_DEVICE=cuda
```

or the equivalent supported runtime.

The API must not need to know whether inference is CPU or GPU based.

---

# 78. External AI Policy

The following are not core production dependencies:

```text
OpenAI
Gemini
Claude
Anthropic APIs
Other external generative-AI APIs
```

External AI may only be introduced if the architecture is explicitly revised.

---

# 79. External Service Policy

External services should be minimized.

Approved infrastructure providers:

```text
Vercel
Supabase
VPS Provider
OpenStreetMap
```

These services provide infrastructure rather than replacing the application's core intelligence.

---

# 80. Data Science Environment

Model training and experimentation may use:

```text
Python
Jupyter
Pandas
NumPy
scikit-learn
XGBoost
PyTorch
OpenCV
```

Training code should remain separate from production inference code.

---

# 81. Training vs Inference Separation

The repository must distinguish:

```text
Training
   ↓
Evaluation
   ↓
Model Artifact
   ↓
Deployment
   ↓
Inference
```

Production workers should not retrain models automatically unless a dedicated training workflow is intentionally implemented.

---

# 82. Dataset Management

Datasets should not be treated as ordinary application source code.

Recommended structure:

```text
data/
├── README.md
├── raw/
├── processed/
├── annotations/
└── evaluation/
```

Large datasets should remain outside Git.

---

# 83. Dataset Versioning

Training experiments should record:

```text
Dataset Version
Model Version
Hyperparameters
Training Date
Evaluation Metrics
Code Version
```

This allows model results to be traced.

---

# 84. AI Experiment Tracking

For initial implementation, experiment metadata may be stored in versioned files and structured database records.

A dedicated experiment tracking platform is not required for MVP.

It may be introduced later if model development becomes sufficiently complex.

---

# 85. Performance Constraints

The platform should target:

### Normal API

Most ordinary CRUD requests:

```text
< 500 ms
```

under normal deployment conditions, excluding large uploads and intentionally long-running operations.

### AI processing

AI processing is asynchronous and has no requirement to complete within a normal API request timeout.

### Dashboard

The initial dashboard should avoid unnecessary blocking requests and parallelize independent data fetching where practical.

These are engineering targets, not guarantees.

---

# 86. File Upload Constraints

Large media must not be unnecessarily routed through the API server.

Preferred:

```text
API → authorize
Client → Storage
API → confirm
```

This reduces backend bandwidth and memory pressure.

---

# 87. API Payload Rules

API responses should avoid returning large media blobs.

Return:

```text
metadata
IDs
URLs / signed URLs
structured results
pagination
```

Large files remain in object storage.

---

# 88. Pagination

Collection endpoints should use pagination.

Example:

```text
?page=1&page_size=25
```

Cursor-based pagination may be introduced for very large datasets.

The exact pagination contract will be defined in `API_SPECIFICATION.md`.

---

# 89. Filtering

Backend filtering should be preferred over downloading all records and filtering in the browser.

Examples:

```text
severity
status
road
segment
date
inspection
maintenance status
geographic region
```

---

# 90. Search

Search should be implemented through backend APIs.

The frontend should not load the entire database for client-side searching.

---

# 91. Technology Boundaries

The following boundaries are mandatory:

```text
Next.js
    ✕ PostgreSQL direct access

Android
    ✕ PostgreSQL direct access

Frontend
    ✕ AI model direct access

FastAPI
    ✓ PostgreSQL

FastAPI
    ✓ Redis

AI Worker
    ✓ Redis

AI Worker
    ✓ PostgreSQL

AI Worker
    ✓ Storage
```

---

# 92. Dependency Ownership

| Technology | Owner |
|---|---|
| Next.js | Web |
| TypeScript | Web |
| Tailwind | Web |
| shadcn/ui | Web |
| Leaflet | Web/GIS |
| FastAPI | Backend |
| SQLAlchemy | Backend |
| PostgreSQL | Data |
| PostGIS | GIS/Data |
| Redis | Infrastructure |
| Celery | Background Processing |
| YOLO | AI |
| PyTorch | AI |
| OpenCV | AI |
| XGBoost | ML |
| scikit-learn | ML |
| Supabase Storage | Infrastructure |
| Kotlin | Android |
| Compose | Android |
| Room | Android |
| WorkManager | Android |
| Retrofit/OkHttp | Android |
| Docker | Infrastructure |
| Nginx | Infrastructure |
| GitHub Actions | CI/CD |

---

# 93. Technologies Explicitly Not Selected

The following are not part of the initial approved architecture:

```text
MongoDB
Firebase as primary backend
Django
Flask
Express
NestJS
Spring Boot
GraphQL
Kubernetes
Kafka
RabbitMQ
OpenAI API
Gemini API
Claude API
AWS as primary managed database
```

This does not mean these technologies are inherently unsuitable.

They are simply outside the approved initial architecture.

---

# 94. Technology Change Process

A technology may be replaced only when the change is documented.

Required evaluation:

```text
Current Problem
      ↓
Proposed Technology
      ↓
Reason
      ↓
Architecture Impact
      ↓
Migration Impact
      ↓
Security Impact
      ↓
Cost Impact
      ↓
Performance Impact
      ↓
Decision
```

After approval:

```text
PROJECT_CONTEXT.md
SYSTEM_ARCHITECTURE.md
TECH_STACK.md
CHANGELOG.md
```

must be updated as applicable.

---

# 95. Final Approved Stack

The final initial production stack is:

```text
WEB
Next.js
React
TypeScript
Tailwind CSS
shadcn/ui
Framer Motion
Recharts
Leaflet

BACKEND
Python
FastAPI
Pydantic
SQLAlchemy
Alembic

DATABASE
PostgreSQL
Supabase
PostGIS

AUTH
JWT
bcrypt
RBAC

AI / ML
PyTorch
YOLO
OpenCV
XGBoost
scikit-learn
Pandas
NumPy
FFmpeg

BACKGROUND PROCESSING
Redis
Celery

STORAGE
Supabase Storage

ANDROID
Kotlin
Jetpack Compose
CameraX
Room
WorkManager
Retrofit
OkHttp
Kotlinx Serialization

INFRASTRUCTURE
Docker
Docker Compose
Nginx
VPS
Vercel

TESTING
Pytest
Vitest
Playwright
JUnit
AndroidX Testing

DEVOPS
Git
GitHub
GitHub Actions
```

---

# 96. Final Technology Principle

The technology stack should remain:

```text
Simple enough for a student/startup team
             +
Strong enough for production
             +
Modular enough for future scaling
             +
AI-capable
             +
Geospatially capable
             +
Offline-capable
```

The initial architecture deliberately avoids unnecessary distributed infrastructure.

The system should begin with:

```text
Next.js
      +
FastAPI
      +
PostgreSQL/PostGIS
      +
Supabase Storage
      +
Redis/Celery
      +
AI Worker
      +
Android
      +
Docker Compose
```

and scale individual components only when actual workload requires it.

---

# 97. Coding-Agent Enforcement

Before implementing any feature, the coding agent must:

1. Read `PROJECT_CONTEXT.md`.
2. Read `PRD.md`.
3. Read `SRS.md`.
4. Read `SYSTEM_ARCHITECTURE.md`.
5. Read this document.
6. Identify the relevant module.
7. Follow the approved technology for that module.
8. Reuse existing infrastructure where possible.
9. Avoid introducing unapproved frameworks.
10. Preserve API contracts.
11. Preserve database integrity.
12. Add tests.
13. Update documentation when architecture changes.
14. Never invent fake production functionality.
15. Never expose secrets.
16. Never replace local AI with an external AI API without explicit architectural approval.

---

# 98. Technology Stack Acceptance Checklist

```text
[ ] Next.js selected for web
[ ] TypeScript selected
[ ] Tailwind selected
[ ] shadcn/ui selected
[ ] Framer Motion selected
[ ] Recharts selected
[ ] Leaflet selected
[ ] FastAPI selected
[ ] SQLAlchemy selected
[ ] Pydantic selected
[ ] PostgreSQL selected
[ ] Supabase selected as managed PostgreSQL
[ ] PostGIS selected
[ ] Alembic selected
[ ] JWT selected
[ ] bcrypt selected
[ ] YOLO selected
[ ] PyTorch selected
[ ] OpenCV selected
[ ] XGBoost selected
[ ] scikit-learn selected
[ ] Redis selected
[ ] Celery selected
[ ] Supabase Storage selected
[ ] Kotlin selected
[ ] Jetpack Compose selected
[ ] CameraX selected
[ ] Room selected
[ ] WorkManager selected
[ ] Docker selected
[ ] Docker Compose selected
[ ] Nginx selected
[ ] Vercel selected
[ ] GitHub Actions selected
[ ] Testing stack selected
[ ] No external generative-AI dependency
[ ] No direct client-to-database access
[ ] AI remains independently deployable
[ ] Future GPU migration remains possible
```

**End of `TECH_STACK.md`**