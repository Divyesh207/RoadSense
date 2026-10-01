# SYSTEM_ARCHITECTURE.md

# Road Intelligence & Pothole Management Platform

**Project Name:** Road Intelligence & Pothole Management Platform  
**Document Type:** System Architecture Specification  
**Version:** 1.0  
**Status:** Approved Architecture Baseline  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`, `SRS.md`  
**Last Updated:** October 2026

---

# 1. Purpose

This document defines the approved technical architecture of the Road Intelligence & Pothole Management Platform.

It describes:

- System boundaries
- Application architecture
- Service architecture
- Data flow
- Deployment architecture
- Frontend architecture
- Android architecture
- Backend architecture
- AI/ML worker architecture
- Storage architecture
- Authentication architecture
- Background processing
- GIS architecture
- Failure isolation
- Scalability
- Security boundaries
- Module dependencies
- Repository structure
- Architectural rules

This document is a technical implementation contract.

Coding agents and developers must follow this architecture unless an architectural change is explicitly approved and documented.

---

# 2. Architectural Vision

The platform shall be designed as a modular, API-first, asynchronous AI-enabled infrastructure intelligence system.

The core architectural principle is:

```text
CLIENTS
   ↓
API
   ↓
BUSINESS SERVICES
   ↓
DATA / JOBS
   ↓
AI PROCESSING
   ↓
INTELLIGENCE
   ↓
OPERATIONAL WORKFLOW
   ↓
HISTORICAL RECORD
```

The system must not be implemented as a collection of disconnected screens or independent AI demonstrations.

---

# 3. Architectural Goals

The architecture must achieve:

1. Clear separation of responsibilities.
2. Secure API-based communication.
3. Local AI inference.
4. Reliable asynchronous processing.
5. Strong data integrity.
6. Historical traceability.
7. Offline-capable field operations.
8. Geospatial intelligence.
9. Explainable road-condition analytics.
10. Scalable AI processing.
11. Easy deployment.
12. Future GPU migration.
13. Maintainable code structure.
14. Testability.
15. Controlled failure behavior.

---

# 4. Architectural Principles

## ARCH-001 — API First

Web and Android clients communicate with the backend through documented APIs.

Clients must not directly access privileged database resources.

---

## ARCH-002 — Backend as System Gateway

The FastAPI backend is the authoritative gateway for:

- Authentication
- Authorization
- Validation
- Business logic
- Workflow transitions
- Database operations
- Job creation
- Audit logging

---

## ARCH-003 — AI as an Independent Processing Layer

AI inference must be isolated from the normal API request lifecycle.

```text
FastAPI
   ↓
Job Queue
   ↓
AI Worker
```

The AI worker may run on the same VPS initially but must remain independently deployable.

---

## ARCH-004 — Database as Source of Application State

PostgreSQL is the authoritative source for structured application state.

Redis is not the permanent source of business records.

---

## ARCH-005 — Object Storage for Large Media

Images, videos, and large evidence files belong in object storage.

PostgreSQL stores metadata and references.

---

## ARCH-006 — Historical Preservation

AI updates must never silently destroy historical information.

Original observations, AI results, human review, maintenance, repair, and verification must remain traceable.

---

## ARCH-007 — No External Generative AI Dependency

Core detection, severity, prediction, and verification functionality must operate using locally deployed models.

No OpenAI, Gemini, Claude, or similar external generative-AI API is required.

---

## ARCH-008 — Human Review Where Required

AI provides analysis and decision support.

Operational records must preserve the distinction between:

```text
AI Result
    ↓
Human Review
    ↓
Final Operational State
```

---

## ARCH-009 — Failure Isolation

Failure of one subsystem should not unnecessarily bring down unrelated platform functionality.

Example:

```text
AI Worker unavailable
        ↓
New AI jobs → QUEUED
        ↓
Dashboard → Still works
        ↓
Road records → Still work
        ↓
Maintenance → Still works
```

---

## ARCH-010 — Version Everything Important

AI models, calculation configurations, and important processing logic must be versioned.

---

# 5. System Context

The complete system consists of:

```text
                         ┌──────────────────────────┐
                         │       Web Client         │
                         │ Next.js + TypeScript     │
                         │ Vercel                   │
                         └────────────┬─────────────┘
                                      │
                                      │ HTTPS REST
                                      │
┌──────────────────────────┐          ▼
│      Android Client     │──────► FastAPI Backend
│ Kotlin + Jetpack        │          │
│ Compose                  │          │
└──────────────────────────┘          │
                                      ├───────────────┐
                                      │               │
                                      ▼               ▼
                               PostgreSQL          Redis
                               Supabase             Queue
                                      │               │
                                      │               ▼
                                      │          AI Worker
                                      │          YOLO / PyTorch
                                      │          OpenCV / XGBoost
                                      │
                                      ▼
                               Supabase Storage
```

---

# 6. High-Level Architecture

The platform is divided into six logical layers.

```text
┌─────────────────────────────────────────────┐
│  Layer 1 — Client Applications              │
│  Web + Android                              │
├─────────────────────────────────────────────┤
│  Layer 2 — API / Gateway                    │
│  FastAPI + Authentication + Authorization   │
├─────────────────────────────────────────────┤
│  Layer 3 — Application Services             │
│  Business Rules + Workflows                 │
├─────────────────────────────────────────────┤
│  Layer 4 — Data & Infrastructure            │
│  PostgreSQL + Object Storage + Redis        │
├─────────────────────────────────────────────┤
│  Layer 5 — AI / ML Processing               │
│  YOLO + OpenCV + XGBoost + PyTorch          │
├─────────────────────────────────────────────┤
│  Layer 6 — Operations                       │
│  Docker + Nginx + Monitoring + Deployment   │
└─────────────────────────────────────────────┘
```

---

# 7. C4-Style System View

## 7.1 System Actors

```text
Administrator
      │
Authority
      │
Inspector
      │
Contractor
      │
      ▼
Road Intelligence Platform
      ▲
      │
AI Worker
      │
Background Worker
```

---

# 8. Container Architecture

The major deployable containers/components are:

```text
Web Application
Android Application
FastAPI API
AI Worker
Redis
Nginx
PostgreSQL
Object Storage
```

The first five are application-controlled components.

PostgreSQL and object storage are managed infrastructure through Supabase.

---

# 9. Physical Deployment Architecture

Initial production deployment:

```text
                         INTERNET
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
          Vercel Web App           Android App
                 │                       │
                 └───────────┬───────────┘
                             │
                           HTTPS
                             │
                             ▼
                    ┌─────────────────┐
                    │      VPS        │
                    │                 │
                    │    Nginx        │
                    │       │         │
                    │       ▼         │
                    │    FastAPI      │
                    │       │         │
                    │   ┌───┴────┐    │
                    │   │        │    │
                    │ Redis    AI Worker
                    │             │    │
                    └─────────────┼────┘
                                  │
                       ┌──────────┴──────────┐
                       ▼                     ▼
                Supabase PostgreSQL   Supabase Storage
```

---

# 10. Network Boundaries

There are four important trust boundaries.

## Boundary 1 — Public Internet

Contains:

- Web users
- Android devices

Only HTTPS traffic is permitted in production.

---

## Boundary 2 — Reverse Proxy

Nginx is the public entry point for the backend VPS.

Responsibilities:

- TLS termination
- Request forwarding
- Basic request protection
- Routing
- Connection handling

---

## Boundary 3 — Application Network

Contains:

- FastAPI
- Redis
- AI worker

These services communicate through the private Docker network.

---

## Boundary 4 — Managed Data Services

Contains:

- Supabase PostgreSQL
- Supabase Storage

Application credentials are stored as server-side secrets.

---

# 11. Web Application Architecture

The web application uses:

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts
Leaflet
```

The web application is deployed on Vercel.

---

# 12. Web Application Layers

The web application should use the following conceptual structure:

```text
Presentation
    ↓
Page / Route
    ↓
UI Components
    ↓
Feature Logic
    ↓
API Client
    ↓
FastAPI
```

The browser must not directly communicate with PostgreSQL.

---

# 13. Next.js Route Structure

The web application should logically separate:

```text
Public Routes
├── Login
└── Authentication-related pages

Protected Routes
├── Dashboard
├── Roads
├── Inspections
├── Damage
├── Map
├── Maintenance
├── Repairs
├── Verification
├── Analytics
├── Reports
├── Notifications
└── Administration
```

Exact route naming will be finalized during UI implementation.

---

# 14. Web Feature Architecture

Each major feature should remain modular.

Example:

```text
features/
├── dashboard/
├── roads/
├── inspections/
├── damage/
├── map/
├── maintenance/
├── verification/
├── recurrence/
├── analytics/
├── reports/
└── administration/
```

Feature modules should contain feature-specific:

- Components
- API functions
- Types
- Validation
- State/query logic
- UI behavior

---

# 15. Web Authentication Flow

```text
User
 ↓
Login Form
 ↓
FastAPI / Auth Endpoint
 ↓
Credential Validation
 ↓
JWT/session issued
 ↓
Web Client stores session securely
 ↓
Authenticated API Requests
 ↓
Backend validates token
 ↓
RBAC check
 ↓
Request processed
```

Authentication implementation must follow `SECURITY.md`.

---

# 16. Web API Client

The web application shall communicate with FastAPI through a centralized API client layer.

Example conceptual structure:

```text
lib/
└── api/
    ├── client
    ├── auth
    ├── roads
    ├── inspections
    ├── damage
    ├── maintenance
    ├── analytics
    └── reports
```

UI components must not contain raw database queries.

---

# 17. Web State Architecture

The UI must distinguish:

```text
Idle
Loading
Success
Empty
Error
Unauthorized
Processing
```

Asynchronous AI workflows should expose backend job states.

Example:

```text
QUEUED
RUNNING
COMPLETED
FAILED
```

---

# 18. GIS Frontend Architecture

Leaflet is responsible for visualization.

Conceptual flow:

```text
FastAPI
   ↓
Geographic Data
   ↓
Web API Client
   ↓
Map Feature Transformation
   ↓
Leaflet
   ↓
Interactive Map
```

The map must not contain business logic for road-health or maintenance-priority calculations.

Those calculations belong to backend services.

---

# 19. Android Architecture

The Android application is a field-operations client.

Technology:

- Kotlin
- Jetpack Compose
- Camera APIs
- Location APIs
- Local persistence
- WorkManager/network synchronization

The architecture should follow a clear separation of:

```text
UI
 ↓
ViewModel
 ↓
Use Case / Repository
 ↓
Local + Remote Data Sources
```

---

# 20. Android Layer Structure

Conceptually:

```text
Presentation
├── Compose Screens
├── UI State
└── ViewModels
        ↓
Domain
├── Inspection Use Cases
├── Upload Use Cases
├── Sync Use Cases
└── Authentication Use Cases
        ↓
Data
├── Repository
├── Local Database
├── Remote API
└── Storage Upload
```

The exact Android local database technology will be finalized in `TECH_STACK.md`.

---

# 21. Android Inspection Architecture

Inspection workflow:

```text
Inspector
   ↓
Create Inspection
   ↓
Capture GPS
   ↓
Capture Image
   ↓
Store Local Metadata
   ↓
Review
   ↓
Queue
   ↓
Synchronize
   ↓
Upload Media
   ↓
Confirm Upload
   ↓
Backend Processing
```

The local queue is authoritative for unsynchronized field work.

---

# 22. Android Offline Architecture

The application must support:

```text
ONLINE
   ↓
Normal API operation

OFFLINE
   ↓
Local persistence
   ↓
Queue
   ↓
Connectivity restored
   ↓
Synchronization
```

The synchronization engine must use stable IDs and idempotency mechanisms.

---

# 23. Backend Architecture

The FastAPI backend is organized into layers.

Recommended architecture:

```text
HTTP / API Layer
        ↓
Application / Service Layer
        ↓
Domain Logic
        ↓
Repository Layer
        ↓
Database / Storage
```

---

# 24. FastAPI API Layer

Responsibilities:

- Route requests
- Parse request data
- Authenticate
- Authorize
- Validate input
- Invoke application services
- Serialize responses
- Return correct HTTP status codes
- Attach request IDs

The API layer should not contain large business algorithms.

---

# 25. Application Service Layer

Application services orchestrate use cases.

Examples:

```text
CreateInspectionService
ProcessInspectionService
ReviewDetectionService
CreateMaintenanceService
SubmitRepairEvidenceService
VerifyRepairService
CalculateRoadHealthService
GeneratePredictionService
DetectRecurrenceService
```

Services coordinate multiple repositories or domain components when required.

---

# 26. Domain Logic

Domain logic contains rules that define platform behavior.

Examples:

- Inspection state transitions
- Maintenance state transitions
- Severity calculation orchestration
- Maintenance priority calculation
- Road-health calculation
- Recurrence rules
- Authorization rules
- Validation rules

Business rules should not be buried inside API route handlers.

---

# 27. Repository Layer

Repositories abstract persistence operations.

Examples:

```text
UserRepository
OrganizationRepository
RoadRepository
SegmentRepository
InspectionRepository
MediaRepository
DamageRepository
MaintenanceRepository
RepairRepository
VerificationRepository
PredictionRepository
AuditRepository
```

Repositories should not contain HTTP-specific behavior.

---

# 28. Database Access

SQLAlchemy is responsible for database interaction.

Conceptually:

```text
FastAPI
   ↓
Service
   ↓
Repository
   ↓
SQLAlchemy
   ↓
PostgreSQL
```

Database credentials must only exist on trusted backend infrastructure.

---

# 29. Database Geospatial Architecture

PostgreSQL should use geospatial capabilities through PostGIS where enabled in the selected Supabase project.

Geospatial entities may include:

```text
Road Geometry
Road Segment Geometry
Inspection Point
Damage Point
Maintenance Location
Repair Location
```

The application should use a consistent geographic reference system.

The exact spatial columns, indexes, and queries will be defined in `DATABASE_SCHEMA.md`.

---

# 30. Road Segment Association Architecture

Road segment association is a backend GIS operation.

Conceptually:

```text
Damage GPS
    ↓
Validate Coordinates
    ↓
Spatial Search
    ↓
Candidate Road Segments
    ↓
Distance / Geometry Check
    ↓
Best Candidate
    ↓
Association Confidence
    ↓
Automatic Association OR Manual Review
```

The frontend must not independently decide authoritative road-segment relationships.

---

# 31. Media Architecture

Large media is stored in Supabase Storage.

The recommended secure flow is:

```text
Client
   ↓
Request Upload Authorization
   ↓
FastAPI validates user
   ↓
FastAPI creates upload metadata
   ↓
Authorized upload URL
   ↓
Client uploads object
   ↓
Client confirms upload
   ↓
FastAPI validates metadata
   ↓
AI job created
```

Storage buckets should remain private unless a specific public asset is intentionally required.

---

# 32. Media Metadata

PostgreSQL stores metadata such as:

```text
media_id
inspection_id
storage_path
media_type
file_size
mime_type
capture_time
uploaded_at
latitude
longitude
source
checksum
```

The exact schema belongs in `DATABASE_SCHEMA.md`.

---

# 33. AI Worker Architecture

The AI worker is an independent processing service.

Conceptual architecture:

```text
Redis Queue
     ↓
AI Worker
     ↓
Job Loader
     ↓
Media Loader
     ↓
Preprocessing
     ↓
Model Inference
     ↓
Postprocessing
     ↓
Business Result
     ↓
PostgreSQL
```

---

# 34. AI Worker Responsibilities

The AI worker may execute:

- Image preprocessing
- Video frame extraction
- YOLO inference
- Detection postprocessing
- Severity calculation
- Repair verification
- Feature generation
- XGBoost prediction
- Model evaluation jobs
- Other long-running AI tasks

The worker must not directly expose its internal APIs to public clients.

---

# 35. AI Model Architecture

The model layer should be modular.

```text
models/
├── detection/
├── severity/
├── verification/
└── prediction/
```

Each model should expose a predictable interface.

Conceptually:

```text
load()
predict()
validate_output()
version()
```

---

# 36. Model Registry Concept

Every deployed model must have identifiable metadata.

Example:

```text
model_family
model_name
model_version
artifact_identifier
configuration_version
trained_at
deployed_at
```

A result must reference the model version that produced it.

---

# 37. YOLO Detection Pipeline

The initial computer-vision pipeline:

```text
Input Image
     ↓
Image Validation
     ↓
Preprocessing
     ↓
YOLO Model
     ↓
Raw Predictions
     ↓
Confidence Filtering
     ↓
Class Mapping
     ↓
Bounding Box Validation
     ↓
Structured Detection
```

No fabricated detection should be created when model inference fails.

---

# 38. Video Processing

For video:

```text
Video
 ↓
Validation
 ↓
Frame Extraction
 ↓
Sampling Strategy
 ↓
Frame Preprocessing
 ↓
YOLO
 ↓
Frame Detections
 ↓
Temporal Aggregation
 ↓
Damage Records
```

The exact frame-sampling and aggregation methodology will be defined in `AI_ML_SPECIFICATION.md`.

---

# 39. Severity Engine

The severity engine consumes validated detection information.

```text
Detection
   ↓
Damage Type
   ↓
Size / Geometry
   ↓
Confidence
   ↓
Additional Available Factors
   ↓
Severity Logic
   ↓
LOW / MEDIUM / HIGH / CRITICAL
```

Severity calculations must be versioned.

---

# 40. Road Health Engine

Road health is a backend/domain intelligence service.

```text
Historical Data
      +
Current Damage
      +
Severity
      +
Recurrence
      +
Repair History
      ↓
Road Health Engine
      ↓
Health Result
```

The calculation must return both:

```text
Health Result
+
Contributing Factors
```

The exact formula belongs to `AI_ML_SPECIFICATION.md` or the analytics specification.

---

# 41. Maintenance Priority Engine

The priority engine consumes road and damage intelligence.

```text
Damage Severity
      +
Damage Age
      +
Road Health
      +
Recurrence
      +
Road Importance
      +
Available Safety / Usage Factors
      ↓
Priority Engine
      ↓
Priority Result
+
Contributing Factors
```

The engine must be deterministic for the same input dataset and configuration version.

---

# 42. Prediction Engine

The prediction engine is responsible for deterioration estimates.

```text
Historical Road Data
        ↓
Feature Generation
        ↓
Feature Validation
        ↓
XGBoost Model
        ↓
Prediction
        ↓
Uncertainty / Confidence
        ↓
Prediction Record
```

If required input data is unavailable:

```text
Insufficient Data
```

must be returned instead of a fabricated prediction.

---

# 43. Repair Verification Architecture

Repair verification compares evidence from before and after maintenance.

```text
Maintenance Job
       ↓
Before Evidence
       +
After Evidence
       ↓
AI Verification Worker
       ↓
Comparison / Analysis
       ↓
Verification Result
       ↓
Human Review
       ↓
Final Maintenance State
```

Historical evidence must remain unchanged.

---

# 44. Recurrence Engine

The recurrence engine compares new observations against historical damage and repair records.

```text
New Damage
    ↓
Location Matching
    ↓
Historical Damage Search
    ↓
Repair History
    ↓
Temporal Comparison
    ↓
Similarity / Rule Evaluation
    ↓
Potential Recurrence
    ↓
Human Confirmation where required
```

A potential recurrence must not automatically be represented as a confirmed recurrence unless the defined rules permit it.

---

# 45. Background Job Architecture

Redis will act as the initial job broker.

The implementation may use a Python task-processing framework such as Celery.

Conceptually:

```text
FastAPI
   ↓
Create Job Record
   ↓
Publish Task
   ↓
Redis
   ↓
Worker
   ↓
Process Task
   ↓
Update PostgreSQL Job State
```

PostgreSQL remains the authoritative source for business/job state.

Redis should not be treated as the permanent record of completed jobs.

---

# 46. Job State Machine

All long-running jobs should use controlled states:

```text
QUEUED
   ↓
RUNNING
   ↓
COMPLETED
```

Failure:

```text
RUNNING
   ↓
FAILED
```

Optional:

```text
QUEUED / RUNNING
       ↓
CANCELLED
```

Retryable failures should increment a retry counter.

---

# 47. Job Idempotency

Every retryable job must have a stable logical identity.

Example:

```text
inspection_id + processing_version
```

This prevents accidental duplicate processing.

The exact idempotency keys will be defined in `API_SPECIFICATION.md`.

---

# 48. Authentication Architecture

Authentication is centralized in FastAPI.

```text
Client
  ↓
Credentials
  ↓
FastAPI
  ↓
Password Verification
  ↓
Token Issuance
  ↓
Authenticated Client
```

Every protected request:

```text
Token
  ↓
Decode
  ↓
Validate
  ↓
Identify User
  ↓
Check Organization Scope
  ↓
Check Role / Permission
  ↓
Execute
```

---

# 49. Authorization Architecture

Authorization must be enforced at the backend.

Conceptually:

```text
Request
 ↓
Authentication
 ↓
User Identity
 ↓
Organization Scope
 ↓
Role
 ↓
Permission
 ↓
Resource Ownership / Access
 ↓
Allow / Deny
```

Frontend route guards are UX mechanisms, not security boundaries.

---

# 50. Organization Isolation

Organization-scoped records must be protected.

Example:

```text
Organization A
 ├── Roads
 ├── Inspections
 ├── Damage
 └── Maintenance

Organization B
 ├── Roads
 ├── Inspections
 ├── Damage
 └── Maintenance
```

A user from Organization A must not access Organization B's protected resources unless explicitly authorized.

---

# 51. Audit Architecture

Important state changes should create audit records.

```text
Business Operation
       ↓
Transaction
       ├── Update Entity
       └── Create Audit Record
```

Where atomicity is required, the entity update and audit record should occur within the same database transaction.

---

# 52. Notification Architecture

Notifications are asynchronous where appropriate.

```text
Business Event
      ↓
Notification Service
      ↓
Notification Record
      ↓
User Notification
```

Examples:

```text
Maintenance Assigned
Repair Submitted
Verification Completed
Recurrence Detected
AI Processing Completed
```

The first implementation may use in-app notifications.

Push notifications can be added later.

---

# 53. Reporting Architecture

Reports may be generated asynchronously for large datasets.

```text
User
 ↓
Report Request
 ↓
FastAPI
 ↓
Report Job
 ↓
Redis
 ↓
Worker
 ↓
Generate PDF / CSV
 ↓
Object Storage
 ↓
Authorized Download
```

Small reports may be generated synchronously where performance permits.

---

# 54. Analytics Architecture

The initial system does not require a separate analytics warehouse.

Analytics can be generated from PostgreSQL using optimized queries.

```text
PostgreSQL
    ↓
Analytics Service
    ↓
Aggregated API Response
    ↓
Recharts / UI
```

If scale later requires a separate analytics platform, it can be introduced without changing the core domain model.

---

# 55. Caching Strategy

Caching should be introduced selectively.

Potential cache candidates:

- Frequently requested dashboard summaries
- Static configuration
- Non-sensitive lookup data
- Expensive aggregate queries

Redis may be used for caching where justified.

Caching must never become the authoritative source of business state.

---

# 56. API Communication Flow

Standard request:

```text
Client
 ↓
HTTPS
 ↓
Nginx
 ↓
FastAPI
 ↓
Authentication
 ↓
Authorization
 ↓
Validation
 ↓
Application Service
 ↓
Repository
 ↓
PostgreSQL
 ↓
Response
```

Long-running request:

```text
Client
 ↓
FastAPI
 ↓
Create Job
 ↓
Return Job ID
 ↓
Redis
 ↓
Worker
 ↓
PostgreSQL
 ↓
Client polls/subscribes for status
```

---

# 57. Inspection Processing Sequence

```text
Inspector
   │
   │ Submit Inspection
   ▼
FastAPI
   │
   ├── Authenticate
   ├── Authorize
   ├── Validate
   └── Create Inspection
   │
   ▼
Storage
   │
   └── Media Uploaded
   │
   ▼
FastAPI
   │
   └── Create AI Job
   │
   ▼
Redis
   │
   ▼
AI Worker
   │
   ├── Load Media
   ├── Preprocess
   ├── YOLO
   ├── Postprocess
   ├── Severity
   └── Persist
   │
   ▼
PostgreSQL
   │
   ▼
Web Dashboard
```

---

# 58. Repair Verification Sequence

```text
Contractor
    ↓
Upload Repair Evidence
    ↓
FastAPI
    ↓
Storage
    ↓
Create Verification Job
    ↓
Redis
    ↓
AI Worker
    ↓
Load Before/After Evidence
    ↓
Verification Model
    ↓
Persist Result
    ↓
Authority Review
    ↓
Maintenance State Updated
```

---

# 59. Offline Synchronization Sequence

```text
Android
   ↓
Create Local Inspection
   ↓
LOCAL_DRAFT
   ↓
QUEUED
   ↓
Connectivity Available?
   ├── No → Remain Queued
   │
   └── Yes
        ↓
     UPLOADING
        ↓
     Backend
        ↓
     Idempotency Check
        ↓
     Store
        ↓
     UPLOADED
        ↓
     PROCESSING
        ↓
     COMPLETED
```

---

# 60. Failure Handling Architecture

## API Failure

```text
Request
 ↓
Validation / Processing Error
 ↓
Structured Error
 ↓
Request ID
 ↓
Client Message
```

---

## AI Failure

```text
AI Job
 ↓
Failure
 ↓
Record Error
 ↓
Retry if Recoverable
 ↓
FAILED if Retry Exhausted
```

The inspection and original media must remain preserved.

---

## Storage Failure

```text
Upload
 ↓
Failure
 ↓
Client Retry / Offline Queue
```

---

## Redis Failure

The API should fail safely.

New asynchronous jobs should not be falsely marked as completed.

Existing database records must remain intact.

---

## Database Failure

The application should return an explicit service/dependency error.

It must not report a successful state when persistence has failed.

---

# 61. Scalability Architecture

The architecture must allow horizontal scaling.

Initial:

```text
1 FastAPI
1 AI Worker
1 Redis
```

Future:

```text
Load Balancer
      ↓
┌─────┼─────┐
API-1 API-2 API-3
      │
      ▼
Redis
      │
┌─────┼────────┐
AI-1  AI-2    AI-GPU
```

---

# 62. Future GPU Migration

The AI worker must communicate through jobs rather than being tightly coupled to the API host.

Initial:

```text
VPS
├── API
└── AI Worker
```

Future:

```text
VPS
└── API
     │
     ▼
   Redis
     │
     ▼
GPU Server
└── AI Worker
```

The frontend, API contracts, and database schema should not require major changes for this migration.

---

# 63. Model Resource Isolation

AI models may require substantial CPU/GPU memory.

The AI worker should therefore be independently configurable for:

```text
CPU
GPU
RAM
Batch Size
Model Path
Worker Count
```

Multiple heavy model processes should not be started blindly on a small production server.

---

# 64. Deployment Architecture

The initial production VPS uses Docker Compose.

Conceptual services:

```yaml
services:
  nginx:
  api:
  ai-worker:
  redis:
```

Supabase remains external:

```text
PostgreSQL
Storage
```

The exact Docker configuration will be defined in `DEPLOYMENT.md`.

---

# 65. Docker Network

Application containers should communicate over a private Docker network.

Example:

```text
internet
   ↓
nginx
   ↓
api
   ├── redis
   └── external Supabase
        ↑
ai-worker
```

Redis should not be publicly exposed.

---

# 66. Persistent Data

The system has two categories of persistent data.

## Application Data

Stored in:

```text
Supabase PostgreSQL
```

Examples:

- Users
- Roads
- Inspections
- Damage
- Maintenance
- Audit records

## Media

Stored in:

```text
Supabase Storage
```

Examples:

- Images
- Videos
- Repair evidence
- Reports

---

# 67. Environment Architecture

Three environments are supported:

```text
Development
     ↓
Staging
     ↓
Production
```

Each environment should have independent:

- Database configuration
- Storage configuration
- JWT secrets
- Redis configuration
- AI model configuration
- API URLs

Production credentials must never be reused in local development.

---

# 68. Configuration Architecture

Configuration should be injected through environment variables.

Conceptual categories:

```text
Application
DATABASE
AUTH
STORAGE
REDIS
AI
CORS
LOGGING
DEPLOYMENT
```

Example:

```text
DATABASE_URL
JWT_SECRET
REDIS_URL
STORAGE_ENDPOINT
STORAGE_ACCESS_KEY
STORAGE_SECRET_KEY
AI_MODEL_PATH
AI_MODEL_VERSION
```

Actual production variable names will be finalized in `DEPLOYMENT.md`.

---

# 69. Observability Architecture

The platform should provide:

```text
Request Logs
      +
Application Logs
      +
AI Worker Logs
      +
Job Status
      +
Health Checks
      +
Error Tracking
```

Every important request should have a request ID.

Long-running jobs should have job IDs.

This enables correlation:

```text
request_id
     ↓
inspection
     ↓
job_id
     ↓
AI worker
     ↓
database result
```

---

# 70. Health Architecture

The API should expose:

```text
/liveness
/readiness
```

Liveness indicates:

```text
Application process is running
```

Readiness indicates:

```text
Application can serve requests
+
Required dependencies are available
```

The exact endpoint paths may be finalized in `API_SPECIFICATION.md`.

---

# 71. Security Architecture

Security is implemented at multiple layers:

```text
HTTPS
 ↓
Nginx
 ↓
Authentication
 ↓
Authorization
 ↓
Input Validation
 ↓
Business Rules
 ↓
Database Permissions
 ↓
Private Storage
```

No single frontend security mechanism should be considered sufficient.

Detailed security requirements belong in `SECURITY.md`.

---

# 72. Storage Security

Private media should use authorized access.

Preferred pattern:

```text
Client
 ↓
Backend authorization
 ↓
Signed / time-limited access
 ↓
Private object
```

Clients must not receive permanent privileged storage credentials.

---

# 73. Data Flow Ownership

Each layer has a defined responsibility.

| Layer | Responsibility |
|---|---|
| Android | Field capture and offline synchronization |
| Web | Visualization and operational interaction |
| FastAPI | Authentication, validation, workflows and APIs |
| Services | Business rules |
| PostgreSQL | Structured application state |
| Storage | Large media |
| Redis | Queue/cache infrastructure |
| AI Worker | Long-running AI/ML processing |
| Nginx | Reverse proxy and TLS |
| Vercel | Web hosting |

---

# 74. Module Dependency Rules

The following dependency direction must be preserved:

```text
API
 ↓
Application Services
 ↓
Domain Logic
 ↓
Repositories
 ↓
Infrastructure
```

The reverse direction should be avoided.

For example:

```text
Repository
  ✕→ UI

Domain
  ✕→ FastAPI Router

AI Model
  ✕→ React Component
```

---

# 75. Shared Package Rules

The shared package may contain:

- API DTO types
- Shared enums
- Documentation schemas
- Non-sensitive constants

It must NOT become a dumping ground for business logic.

The backend remains authoritative for business rules.

---

# 76. AI / Application Boundary

The AI worker should return structured results.

Example conceptual output:

```json
{
  "model": {
    "name": "road-damage-detector",
    "version": "1.0.0"
  },
  "detections": [
    {
      "class": "POTHOLE",
      "confidence": 0.94,
      "bbox": [120, 80, 420, 310]
    }
  ]
}
```

The exact schema will be defined in `AI_ML_SPECIFICATION.md` and `API_SPECIFICATION.md`.

---

# 77. No Fake AI Architecture

The production architecture must never use:

```text
Upload Image
   ↓
Hard-coded "Pothole Detected"
```

as a substitute for actual inference.

If AI infrastructure is unavailable:

```text
AI Job
 ↓
FAILED / QUEUED
```

must be represented honestly.

Development mocks may exist only in isolated test environments.

---

# 78. Data Processing Boundary

The system distinguishes:

```text
Raw Observation
       ↓
AI Output
       ↓
Reviewed Result
       ↓
Business Intelligence
       ↓
Operational Action
```

These stages must not be collapsed into one mutable record.

---

# 79. Historical Data Architecture

Historical records must be append-oriented wherever practical.

Example:

```text
Inspection 1
   ↓
Detection 1
   ↓
Maintenance 1
   ↓
Repair 1
   ↓
Verification 1
   ↓
Inspection 2
   ↓
Potential Recurrence
```

A new AI model must not rewrite the original historical observation without creating an explicit new processing/review record.

---

# 80. Architecture for Reprocessing

The system should support future model reprocessing.

Example:

```text
Original Media
     ↓
Model v1
     ↓
Detection Result v1

Original Media
     ↓
Model v2
     ↓
Detection Result v2
```

Both results can remain traceable.

The latest reviewed/approved result can be separately identified.

---

# 81. Architecture for Model Rollback

If a new model produces unacceptable results, the deployed model version can be changed without deleting previous results.

```text
Model v1 → Previous
Model v2 → Current
Model v3 → Candidate

Rollback:
v3 → disabled
v2 → current
```

Model deployment status must be distinct from historical result records.

---

# 82. Road Intelligence Pipeline

The complete intelligence architecture is:

```text
Raw Inspection
      ↓
Media
      ↓
Detection
      ↓
Classification
      ↓
Severity
      ↓
Geographic Association
      ↓
Road Segment
      ↓
Road Health
      ↓
Maintenance Priority
      ↓
Prediction
      ↓
Maintenance
      ↓
Repair Verification
      ↓
Recurrence
      ↓
Historical Intelligence
```

---

# 83. Architectural Sequence — Complete Lifecycle

```text
┌────────────┐
│ Inspector  │
└─────┬──────┘
      │
      ▼
Capture Image + GPS
      │
      ▼
┌────────────┐
│  Android   │
└─────┬──────┘
      │ HTTPS
      ▼
┌────────────┐
│  FastAPI   │
└─────┬──────┘
      │
      ├──────────────► PostgreSQL
      │
      └──────────────► Storage
                         │
                         ▼
                       Job
                         │
                         ▼
                      Redis
                         │
                         ▼
                   ┌────────────┐
                   │ AI Worker  │
                   └─────┬──────┘
                         │
                  ┌──────┴──────┐
                  │             │
                 YOLO        XGBoost
                  │             │
                  └──────┬──────┘
                         ▼
                    PostgreSQL
                         │
                         ▼
                  Road Intelligence
                         │
                         ▼
                    Web Dashboard
                         │
                         ▼
                  Maintenance Job
                         │
                         ▼
                     Repair
                         │
                         ▼
                  Repair Evidence
                         │
                         ▼
                   AI Verification
                         │
                         ▼
                 Historical Record
                         │
                         ▼
                  Recurrence Engine
```

---

# 84. Repository Architecture

The approved monorepo structure is:

```text
road-intelligence-platform/
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── lib/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── tests/
│   │
│   └── android/
│       └── ...
│
├── services/
│   ├── api/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── domain/
│   │   │   ├── jobs/
│   │   │   └── tests/
│   │   └── ...
│   │
│   └── ai-worker/
│       ├── worker/
│       ├── models/
│       ├── pipelines/
│       ├── inference/
│       ├── preprocessing/
│       ├── postprocessing/
│       ├── tests/
│       └── ...
│
├── packages/
│   └── shared/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── scripts/
│
├── docs/
│
├── data/
│   └── README.md
│
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

This structure may be refined during implementation but the logical boundaries must remain.

---

# 85. Backend Internal Structure

Recommended:

```text
services/api/app/

├── main.py

├── api/
│   ├── v1/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── roads.py
│   │   ├── segments.py
│   │   ├── inspections.py
│   │   ├── damage.py
│   │   ├── maintenance.py
│   │   ├── repairs.py
│   │   ├── verification.py
│   │   ├── predictions.py
│   │   ├── analytics.py
│   │   ├── reports.py
│   │   └── notifications.py
│   └── dependencies.py

├── core/
│   ├── config.py
│   ├── security.py
│   ├── logging.py
│   └── errors.py

├── models/
├── schemas/
├── repositories/
├── services/
├── domain/
├── jobs/
└── tests/
```

The exact file structure can evolve, but responsibilities must remain separated.

---

# 86. AI Worker Internal Structure

Recommended:

```text
services/ai-worker/

├── worker/
│   ├── app.py
│   ├── tasks.py
│   └── queue.py
│
├── models/
│   ├── registry.py
│   ├── detection/
│   ├── severity/
│   ├── verification/
│   └── prediction/
│
├── preprocessing/
├── inference/
├── postprocessing/
├── pipelines/
├── storage/
├── database/
└── tests/
```

AI-specific code must remain independent from frontend code.

---

# 87. Architectural Anti-Patterns

The following are prohibited unless explicitly approved:

### Anti-pattern 1

Frontend → PostgreSQL directly.

### Anti-pattern 2

Frontend → AI model directly.

### Anti-pattern 3

API request waits several minutes for AI inference.

### Anti-pattern 4

AI worker directly controls UI state.

### Anti-pattern 5

Hard-coded fake AI results.

### Anti-pattern 6

Business logic inside React components.

### Anti-pattern 7

Business logic inside FastAPI route handlers.

### Anti-pattern 8

Permanent private storage credentials inside mobile/web applications.

### Anti-pattern 9

Using Redis as the permanent source of business truth.

### Anti-pattern 10

Deleting historical AI results after model updates.

### Anti-pattern 11

Creating a new framework or infrastructure service for a problem that existing architecture can solve.

### Anti-pattern 12

Allowing one organization's records to leak into another organization's scope.

---

# 88. Performance Architecture

Performance priorities:

## Priority 1

Keep normal API requests fast.

## Priority 2

Move expensive operations to workers.

## Priority 3

Avoid unnecessary database queries.

## Priority 4

Use pagination.

## Priority 5

Use spatial indexes for geographic queries.

## Priority 6

Use object storage for large files.

## Priority 7

Use caching only where justified.

## Priority 8

Scale AI workers independently.

---

# 89. Reliability Architecture

Reliability mechanisms include:

```text
Validation
+
Transactions
+
Idempotency
+
Retries
+
Persistent Job State
+
Offline Queue
+
Historical Preservation
+
Health Checks
+
Structured Errors
```

The system should prefer explicit failure over silent corruption.

---

# 90. Security Boundaries

Sensitive operations require:

```text
Authentication
      +
Authorization
      +
Validation
      +
Audit Logging
```

Examples:

- User management
- Role changes
- Maintenance assignment
- Detection review
- Severity correction
- Verification decisions
- Report generation
- Administrative configuration

---

# 91. Architecture Change Management

Any significant architectural change must update:

1. `PROJECT_CONTEXT.md` if the master decision changes.
2. `SYSTEM_ARCHITECTURE.md`
3. Relevant technical specification.
4. `CHANGELOG.md`

Examples of changes requiring documentation:

- Database change
- Authentication change
- New AI provider
- New framework
- Deployment architecture change
- New service
- Major API design change
- Storage architecture change

---

# 92. Decision Authority

When implementation conflicts with architecture:

```text
Approved Documentation
        ↓
Architecture
        ↓
Implementation
```

Existing code does not automatically override approved architecture.

If code conflicts with the specification, the conflict must be identified.

---

# 93. Architecture Acceptance Criteria

The architecture is considered correctly implemented when:

```text
[ ] Web communicates through FastAPI
[ ] Android communicates through FastAPI
[ ] Clients do not access PostgreSQL directly
[ ] Authentication is centralized
[ ] RBAC is enforced server-side
[ ] Large media uses object storage
[ ] AI processing is asynchronous
[ ] AI worker is independently deployable
[ ] Redis is used for job infrastructure
[ ] PostgreSQL remains source of truth
[ ] AI models are versioned
[ ] Historical results are preserved
[ ] Road/segment GIS relationships are traceable
[ ] Maintenance workflow is state-controlled
[ ] Repair verification is traceable
[ ] Recurrence is linked to historical records
[ ] Production services are containerized
[ ] Nginx protects the backend entry point
[ ] AI worker can later move to GPU infrastructure
[ ] No core external generative-AI dependency exists
[ ] Secrets remain outside source control
[ ] Logs and health checks exist
```

---

# 94. Final Architecture

The approved architecture is:

```text
                         USERS
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
    Next.js Web                        Android App
      Vercel                           Kotlin/Compose
          │                                 │
          └──────────────┬──────────────────┘
                         │
                       HTTPS
                         │
                         ▼
                  ┌─────────────┐
                  │    Nginx    │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   FastAPI   │
                  │     API     │
                  └──────┬──────┘
                         │
             ┌───────────┼───────────┐
             │           │           │
             ▼           ▼           ▼
        PostgreSQL     Redis       Storage
        Supabase       Queue       Supabase
             │           │
             │           ▼
             │      ┌───────────┐
             │      │ AI Worker │
             │      └─────┬─────┘
             │            │
             │      ┌─────┴──────┐
             │      │            │
             │     YOLO       XGBoost
             │   OpenCV       sklearn
             │      │            │
             └──────┴────────────┘
                         │
                         ▼
                ROAD INTELLIGENCE
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          Road Health  Priority  Prediction
              │          │          │
              └──────────┼──────────┘
                         ▼
                   MAINTENANCE
                         │
                         ▼
                     REPAIR
                         │
                         ▼
                  AI VERIFICATION
                         │
                         ▼
                    RECURRENCE
                         │
                         ▼
               HISTORICAL INTELLIGENCE
```

---

# 95. Master Architecture Principle

The platform must maintain the following separation:

```text
CLIENT
  ↓
API
  ↓
BUSINESS LOGIC
  ↓
PERSISTENCE
  ↓
ASYNC PROCESSING
  ↓
AI / ML
  ↓
INTELLIGENCE
  ↓
OPERATIONS
  ↓
VERIFICATION
  ↓
HISTORY
```

No layer should bypass another layer without an explicit architectural reason.

The architecture exists to ensure that the platform remains:

- Modular
- Secure
- Traceable
- Testable
- Explainable
- Scalable
- Deployable
- Maintainable

The final system is therefore not merely:

```text
Camera → YOLO → Pothole
```

It is:

```text
Field Observation
      ↓
Secure Data Ingestion
      ↓
AI Analysis
      ↓
Geospatial Intelligence
      ↓
Road Health
      ↓
Deterioration Analysis
      ↓
Maintenance Prioritization
      ↓
Operational Workflow
      ↓
Repair Verification
      ↓
Recurrence Monitoring
      ↓
Historical Road Intelligence
```

This architecture is the baseline that all subsequent technical documents and implementation work must follow.