# Road Intelligence & Pothole Management Platform
## Implementation Roadmap

**Document:** 15_ROADMAP.md  
**Status:** APPROVED FOR IMPLEMENTATION  
**Version:** 1.0  
**Date:** 2026-10-01  
**Parent Documents:** 01_PROJECT_CONTEXT.md → 14_TESTING_STRATEGY.md

---

# 1. Purpose

This document defines the implementation roadmap for the Road Intelligence & Pothole Management Platform.

The roadmap converts the approved product requirements, software requirements, architecture, database schema, API specification, AI/ML specification, security model, deployment architecture, Android specification, UI/UX specification, and testing strategy into an ordered implementation sequence.

The coding agent MUST follow this roadmap as an implementation dependency plan.

The project MUST NOT be implemented as a collection of disconnected screens or isolated features.

The implementation must progressively establish the complete lifecycle:

```text
Foundation
    ↓
Authentication & Organization
    ↓
Road & Segment Management
    ↓
Inspection & Evidence Collection
    ↓
AI Processing
    ↓
Damage Intelligence
    ↓
GIS Intelligence
    ↓
Road Health
    ↓
Deterioration Prediction
    ↓
Maintenance Management
    ↓
Repair Evidence
    ↓
Repair Verification
    ↓
Recurrence Tracking
    ↓
Analytics & Historical Intelligence
    ↓
Production Hardening
```

---

# 2. Roadmap Principles

## 2.1 Dependency Before Feature

A feature MUST NOT be implemented before its required foundation exists.

For example:

```text
Authentication
    ↓
Organization context
    ↓
Road
    ↓
Road Segment
    ↓
Inspection
    ↓
Media
    ↓
AI Processing
    ↓
Damage
```

The coding agent must not bypass these dependencies using fake data or temporary architectural shortcuts.

---

## 2.2 Backend Contract Before Client Integration

For cross-platform features, the preferred sequence is:

```text
Database Model
    ↓
Migration
    ↓
Domain/Application Logic
    ↓
API Endpoint
    ↓
API Tests
    ↓
Web Integration
    ↓
Android Integration
    ↓
E2E Testing
```

This ensures the Web and Android applications use the same authoritative backend contracts.

---

## 2.3 Real Functionality Over Visual Completion

A UI screen is not considered implemented simply because it renders.

A feature is complete only when:

- UI exists
- API integration exists
- authorization exists
- validation exists
- database persistence exists where required
- error handling exists
- loading states exist
- empty states exist
- audit behavior exists where applicable
- tests exist
- state transitions are enforced
- real data flows through the feature

---

# 3. Master Development Phases

The implementation is divided into the following phases.

| Phase | Name | Primary Objective |
|---|---|---|
| 0 | Project Initialization | Establish repository and engineering foundation |
| 1 | Backend Foundation | Establish FastAPI architecture and infrastructure |
| 2 | Database Foundation | Implement PostgreSQL/PostGIS schema |
| 3 | Authentication & RBAC | Establish secure multi-tenant access |
| 4 | Road Intelligence Foundation | Implement roads and segments |
| 5 | Inspection Backend | Implement inspection lifecycle and evidence |
| 6 | AI Processing Pipeline | Implement real AI processing |
| 7 | Damage Intelligence | Implement canonical damage lifecycle |
| 8 | Web Application Core | Implement production web shell and workflows |
| 9 | GIS & Road Health | Implement spatial and health intelligence |
| 10 | Prediction | Implement deterioration prediction |
| 11 | Maintenance | Implement maintenance lifecycle |
| 12 | Repair Verification | Implement post-repair verification |
| 13 | Recurrence & Historical Intelligence | Implement long-term road intelligence |
| 14 | Android Field Application | Implement complete field workflow |
| 15 | Analytics & Reporting | Implement operational intelligence |
| 16 | Production Hardening | Security, reliability, performance, observability |
| 17 | System Validation | Full E2E and release validation |
| 18 | Production Release | Deploy and monitor production system |

---

# 4. Phase 0 — Project Initialization

## Objective

Create the repository structure and engineering standards.

## Tasks

### 4.1 Repository

Create:

```text
road-intelligence-platform/
├── apps/
│   ├── web/
│   └── android/
├── services/
│   ├── api/
│   └── ai-worker/
├── packages/
│   └── shared/
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── scripts/
├── docs/
├── data/
│   └── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 4.2 Documentation

Copy the approved specification documents into:

```text
docs/
```

The coding agent MUST treat these documents as implementation specifications.

---

## 4.3 Development Standards

Configure:

### Backend

- Python 3.12+
- Ruff
- Pytest
- type checking
- environment configuration
- structured logging

### Web

- TypeScript strict mode
- ESLint
- Prettier
- Vitest
- Playwright

### Android

- Kotlin
- Android lint
- formatting
- JUnit
- AndroidX testing

---

## 4.4 Git Strategy

Recommended branches:

```text
main
develop
feature/*
fix/*
hotfix/*
```

No secrets may be committed.

---

## Exit Criteria

- Repository structure exists.
- Applications can start independently.
- API health endpoint exists.
- Web application starts.
- Android project builds.
- Docker Compose configuration exists.
- CI skeleton exists.
- Documentation is available.

---

# 5. Phase 1 — Backend Foundation

## Objective

Establish the FastAPI service architecture.

## Implementation

Create:

```text
services/api/
├── app/
│   ├── main.py
│   ├── core/
│   ├── api/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   ├── domain/
│   ├── workers/
│   └── utils/
├── tests/
├── alembic/
├── requirements/
└── Dockerfile
```

---

## Core Components

Implement:

- FastAPI application
- configuration system
- database connection
- SQLAlchemy session management
- Alembic
- API versioning
- request ID middleware
- structured logging
- exception handling
- validation
- CORS
- health endpoints

Endpoints:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
```

---

## Exit Criteria

- FastAPI starts.
- Database connection mechanism works.
- Alembic works.
- Health endpoints work.
- Standard error envelope works.
- Request IDs are generated and propagated.
- Tests execute successfully.

---

# 6. Phase 2 — Database Foundation

## Objective

Implement the authoritative PostgreSQL/PostGIS data model.

---

## 6.1 Database Extensions

Enable:

```sql
postgis
pgcrypto
```

---

## 6.2 Core Tables

Implement the schema defined in:

```text
06_DATABASE_SCHEMA.md
```

Initial migration groups:

### Identity

```text
organizations
users
roles
permissions
role_permissions
organization_memberships
refresh_tokens
```

### Road

```text
roads
road_segments
```

### Inspection

```text
inspections
inspection_media
processing_jobs
```

### AI

```text
ai_models
ai_processing_runs
damage_types
ai_detections
damage_records
damage_reviews
```

### Intelligence

```text
road_health_snapshots
maintenance_priority_snapshots
deterioration_predictions
```

### Maintenance

```text
maintenance_jobs
maintenance_damage_links
maintenance_status_history
repair_evidence
repair_verifications
recurrence_records
```

### Platform

```text
notifications
generated_reports
audit_logs
```

---

## 6.3 Spatial Configuration

Use:

```text
SRID: 4326
```

for application-level geographic coordinates.

Required spatial types:

```text
roads              LINESTRING
road_segments      LINESTRING
inspections        POINT
detections         POINT
damage_records     POINT
maintenance_jobs   POINT
repair_evidence    POINT
```

Add appropriate GiST indexes.

---

## 6.4 Database Constraints

Implement constraints for:

- valid UUIDs
- valid confidence values
- valid severity
- valid statuses
- organization ownership
- timestamps
- model version references
- state transitions where practical
- required relationships

---

## Exit Criteria

- All required tables exist.
- Alembic migration succeeds on a clean database.
- Spatial queries work.
- Relationships and indexes are verified.
- Database tests pass.
- Organization isolation can be tested.

---

# 7. Phase 3 — Authentication & RBAC

## Objective

Establish secure multi-tenant access before implementing operational features.

---

## 7.1 Authentication

Implement:

```text
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
POST /auth/change-password
```

Use:

```text
JWT
bcrypt
short-lived access token
secure refresh mechanism
```

---

## 7.2 Organization Context

Implement:

```text
X-Organization-ID
```

and server-side validation.

The server MUST verify that the authenticated user belongs to the requested organization.

---

## 7.3 Roles

Implement:

```text
ADMINISTRATOR
ROAD_AUTHORITY
FIELD_INSPECTOR
CONTRACTOR
```

Worker identities must be separated from normal users.

---

## 7.4 Authorization

Every protected resource must follow:

```text
Authenticate
→ Resolve User
→ Resolve Organization
→ Resolve Membership
→ Resolve Role
→ Check Permission
→ Check Resource Ownership
→ Check State Transition
→ Allow/Deny
```

---

## Exit Criteria

- Login works.
- JWT validation works.
- Organization isolation works.
- RBAC works.
- 401/403 behavior works.
- Privilege escalation tests pass.
- Cross-organization access tests pass.

---

# 8. Phase 4 — Road Intelligence Foundation

## Objective

Implement the authoritative road and road-segment model.

---

## Features

### Road

Implement:

- create road
- list roads
- view road
- update road
- road metadata
- road geometry

### Road Segment

Implement:

- create segment
- update segment
- segment geometry
- road relationship
- segment metadata
- spatial queries

---

## GIS Association

Implement:

```text
GPS coordinate
    ↓
PostGIS spatial query
    ↓
Candidate road
    ↓
Candidate segment
    ↓
Association
```

Uncertain matches must be represented explicitly.

---

## Exit Criteria

A user can:

```text
Create Road
→ Create Segments
→ View Road
→ View Segments
→ View Geometry
→ Retrieve by Map Bounds
```

---

# 9. Phase 5 — Inspection Backend

## Objective

Implement the complete inspection lifecycle.

---

## State Machine

```text
DRAFT
 ↓
SUBMITTED
 ↓
UPLOADING
 ↓
PROCESSING
 ↓
ANALYZED
 ↓
REVIEW_REQUIRED
 ↓
REVIEWED
 ↓
COMPLETED
```

Failure states:

```text
UPLOAD_FAILED
PROCESSING_FAILED
ANALYSIS_FAILED
```

---

## Features

Implement:

- inspection creation
- inspection metadata
- GPS capture
- road/segment association
- media metadata
- signed upload URLs
- upload completion
- submission
- processing request
- processing status
- inspection history

---

## Evidence Requirements

Every inspection must preserve:

```text
WHO
WHAT
WHERE
WHEN
MEDIA
DEVICE/CLIENT IDENTIFIER
PROCESSING STATUS
AI PROCESSING RESULT
```

---

## Exit Criteria

A complete inspection can be created through API and processed through its lifecycle.

---

# 10. Phase 6 — AI Processing Pipeline

## Objective

Introduce the real local AI processing system.

---

## Architecture

```text
Inspection
    ↓
Processing Job
    ↓
Redis
    ↓
Celery Worker
    ↓
Media Validation
    ↓
OpenCV Preprocessing
    ↓
YOLO
    ↓
Post-processing
    ↓
Damage Classification
    ↓
Severity Assessment
    ↓
Geospatial Association
    ↓
Canonical Damage
```

---

## AI Model Classes

Initial classes:

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

---

## Model Registry

Implement:

```text
ai_models
ai_processing_runs
```

Every AI result must identify:

```text
model_id
model_version
processing_run_id
timestamp
input reference
```

---

## AI Rules

The system MUST NOT:

- fabricate detections
- fabricate confidence
- silently replace previous results
- call external generative AI APIs
- hide low-confidence predictions as confirmed damage

---

## Exit Criteria

A real uploaded image can produce a persisted AI processing result.

---

# 11. Phase 7 — Damage Intelligence

## Objective

Convert AI detections into operational damage records.

---

## Pipeline

```text
Raw AI Detection
       ↓
Candidate Damage
       ↓
Human Review
       ↓
Confirmed / Rejected / Corrected
       ↓
Canonical Damage Record
```

---

## Features

Implement:

- damage list
- damage detail
- filtering
- map location
- damage type
- confidence
- severity
- status
- review
- correction
- reviewer notes
- audit trail

---

## Human Review

Review actions:

```text
CONFIRM
REJECT
CORRECT TYPE
CORRECT SEVERITY
ADD NOTE
```

The original AI output MUST remain unchanged.

---

## Exit Criteria

An inspector/authority can review an AI detection and produce an auditable canonical damage record.

---

# 12. Phase 8 — Web Application Core

## Objective

Build the main operational web application around real backend APIs.

---

# 12.1 Application Shell

Implement:

```text
Login
Application Shell
Sidebar
Top Bar
Organization Selector
User Menu
Notifications
Global Search
```

---

# 12.2 Dashboard

Initial dashboard:

```text
Roads Monitored
Active Damages
Critical Damages
Maintenance Pending
```

Additional sections:

- damage trend
- road health
- map
- maintenance status
- recent inspections
- recurrence indicators

---

# 12.3 Road UI

Implement:

```text
Road List
Road Detail
Segment List
Segment Detail
Map View
Damage History
Health History
Maintenance History
```

---

# 12.4 Inspection UI

Implement:

```text
Inspection List
Inspection Detail
Media Viewer
Processing Status
AI Results
Review Interface
```

---

## Exit Criteria

Web users can perform the core operational workflow without mock APIs.

---

# 13. Phase 9 — GIS & Road Health

## Objective

Transform raw damage data into spatial road intelligence.

---

## GIS Layers

Implement:

```text
Roads
Road Segments
Damages
Inspections
Maintenance
Repair Evidence
```

---

## Map Capabilities

Implement:

- pan/zoom
- layer toggles
- bounding-box querying
- marker/feature clustering where appropriate
- detail interaction
- road/segment selection
- damage filtering
- severity filtering
- date filtering

---

# 13.1 Road Health

Create historical snapshots containing measurable factors.

Candidate factors:

```text
Damage density
Damage count
Severity distribution
Unresolved damage
Recent inspection freshness
Historical trend
Recurrence
Maintenance history
```

The exact health calculation must be defined in implementation configuration and documented.

It MUST NOT be presented as scientifically validated unless validated against appropriate data.

---

## Exit Criteria

Users can select a road segment and understand:

```text
Current Condition
Historical Condition
Damage Distribution
Maintenance History
Health Trend
```

---

# 14. Phase 10 — Deterioration Prediction

## Objective

Implement predictive road intelligence only after sufficient historical data exists.

---

## Important Dependency

The prediction model MUST NOT be treated as a prerequisite for the basic operational system.

The system must function correctly without predictions.

---

## Prediction Pipeline

```text
Historical Data
    ↓
Feature Generation
    ↓
Feature Snapshot
    ↓
Validation
    ↓
XGBoost
    ↓
Prediction
    ↓
Persist Model Version
    ↓
Persist Prediction
```

---

## Candidate Features

Examples:

```text
historical damage count
damage density
severity distribution
unresolved damage
recurrence
inspection frequency
inspection freshness
road health trend
maintenance history
time since maintenance
```

Only features actually available in the database may be used.

---

## Data Leakage Prevention

Use time-aware and segment-aware validation.

Never use future information to predict a historical target.

---

## Prediction Output

Store:

```text
road segment
prediction type
prediction value
horizon
model version
feature version
timestamp
input snapshot
uncertainty/confidence where supported
```

---

## Exit Criteria

Prediction functionality is released only when:

- target definition exists
- dataset version exists
- validation exists
- leakage checks pass
- model version exists
- model artifact is reproducible
- prediction output is auditable

If insufficient data exists, the UI must clearly indicate that prediction is unavailable rather than fabricating a result.

---

# 15. Phase 11 — Maintenance Management

## Objective

Convert identified damage into operational maintenance work.

---

## Maintenance State Machine

```text
OPEN
 ↓
ASSIGNED
 ↓
IN_PROGRESS
 ↓
COMPLETED
 ↓
VERIFICATION_PENDING
 ↓
VERIFIED
```

Alternative paths:

```text
IN_PROGRESS → CANCELLED

VERIFICATION_PENDING → REJECTED

REJECTED → IN_PROGRESS
```

---

## Features

Implement:

- create maintenance job
- link damages
- assign contractor
- priority
- due date
- status
- notes
- work history
- status history
- maintenance dashboard

---

## Priority

Maintenance priority must be based on explicit measurable factors.

Potential inputs:

```text
severity
damage count
road health
recurrence
location context
maintenance history
age of unresolved damage
```

The system must retain the factors used to produce the priority.

---

## Exit Criteria

A confirmed damage can be converted into an auditable maintenance workflow.

---

# 16. Phase 12 — Repair Evidence & Verification

## Objective

Verify that maintenance work actually addressed the recorded issue.

---

# 16.1 Repair Evidence

Support:

- image upload
- timestamp
- GPS
- maintenance job
- contractor
- notes
- evidence metadata

---

# 16.2 Verification

Pipeline:

```text
Maintenance Completed
        ↓
Repair Evidence
        ↓
AI Verification
        ↓
Verification Result
        ↓
Human Review
        ↓
Verified / Rejected
```

---

## Critical Rule

AI verification does NOT equal human approval.

The system must distinguish:

```text
AI Verification Result
```

from:

```text
Human Verification Decision
```

---

## Exit Criteria

A maintenance job cannot become fully verified merely because an AI model produced a positive result.

---

# 17. Phase 13 — Recurrence & Historical Intelligence

## Objective

Track whether damage returns after maintenance.

---

## Recurrence Logic

Conceptually:

```text
Original Damage
      ↓
Maintenance
      ↓
Repair Evidence
      ↓
Verification
      ↓
Later Inspection
      ↓
Spatial/Temporal Matching
      ↓
Potential Recurrence
      ↓
Recurrence Record
```

---

## Recurrence Data

Store:

```text
original damage
maintenance job
repair verification
new damage
spatial relationship
temporal relationship
detection confidence
human review
recurrence status
```

---

## Historical Intelligence

Road history must allow users to understand:

```text
Damage
→ Maintenance
→ Repair
→ Verification
→ Later Damage
→ Recurrence
```

Historical records MUST NOT be silently overwritten.

---

## Exit Criteria

A road segment can display its historical maintenance and recurrence lifecycle.

---

# 18. Phase 14 — Android Field Application

## Objective

Implement the field collection application after the backend contracts are stable.

---

## Navigation

```text
Splash
 ↓
Authentication
 ↓
Home
 ├── New Inspection
 ├── Inspections
 ├── Sync Queue
 └── Profile
```

---

# 18.1 Inspection Workflow

```text
Create Local Inspection
        ↓
Select Road/Segment
        ↓
Capture GPS
        ↓
Capture Image/Video
        ↓
Validate Evidence
        ↓
Save to Room
        ↓
Queue Sync
        ↓
Upload
        ↓
Submit
        ↓
Backend Processing
```

---

# 18.2 Offline Mode

The app MUST continue to support:

```text
LOCAL_DRAFT
→ QUEUED
→ UPLOADING
→ UPLOADED
→ PROCESSING
→ COMPLETED
```

Failure:

```text
UPLOAD_FAILED
→ RETRY
```

---

# 18.3 WorkManager

Use WorkManager for:

- upload retry
- queued inspection synchronization
- background processing status refresh where appropriate

Use exponential backoff for transient failures.

---

# 18.4 Camera

Use CameraX.

Capture:

- image
- optional video
- metadata
- timestamp

Avoid unnecessary battery consumption.

---

## Exit Criteria

A field inspector can complete a full inspection:

```text
Offline
→ Capture
→ Save
→ Reconnect
→ Sync
→ Process
→ View Result
```

---

# 19. Phase 15 — Analytics & Reporting

## Objective

Provide operational and historical intelligence.

---

## Analytics

Implement:

### Damage Analytics

- damage count
- type distribution
- severity distribution
- trend over time
- geographic distribution

### Road Analytics

- health trend
- damage density
- recurring segments
- unresolved damage

### Maintenance Analytics

- open jobs
- completed jobs
- verification status
- repair cycle time
- recurrence after repair

### Inspection Analytics

- inspections over time
- inspector activity
- processing status
- failed uploads
- AI processing statistics

---

# 19.1 Reports

Reports are generated asynchronously.

Flow:

```text
Report Request
    ↓
Background Job
    ↓
Generate Report
    ↓
Store Report
    ↓
Create Download URL
```

Reports MUST NOT block API requests for long-running generation.

---

## Exit Criteria

Users can generate and download operational reports based on actual persisted data.

---

# 20. Phase 16 — Production Hardening

## Objective

Harden the complete platform for production.

---

# 20.1 Security

Validate:

- JWT
- RBAC
- organization isolation
- IDOR
- rate limits
- CORS
- XSS
- CSRF
- SSRF
- SQL injection
- path traversal
- malicious uploads
- signed URLs
- secret exposure
- privilege escalation

---

# 20.2 Performance

Validate:

```text
API latency
database query performance
spatial query performance
map loading
dashboard loading
media upload
AI processing throughput
worker queue behavior
Android sync
```

---

# 20.3 Reliability

Test:

- API restart
- Redis restart
- worker restart
- failed AI job
- failed upload
- expired JWT
- database connection failure
- storage failure
- network loss
- Android process termination

---

# 20.4 Observability

Implement:

```text
structured logs
request IDs
job IDs
processing IDs
health checks
worker monitoring
error monitoring
basic operational metrics
```

---

# 20.5 Backup & Recovery

Validate:

```text
database backup
database restore
storage recovery
configuration recovery
deployment recovery
model artifact recovery
```

---

# 21. Phase 17 — Complete System Validation

## Objective

Validate the complete system against the approved specifications.

---

# 21.1 Master E2E Scenario

Execute:

```text
Administrator
    ↓
Create Organization
    ↓
Create Users
    ↓
Assign Roles
    ↓
Create Road
    ↓
Create Road Segments
    ↓
Field Inspector Login
    ↓
Create Inspection
    ↓
Capture GPS
    ↓
Capture Media
    ↓
Offline Queue
    ↓
Synchronize
    ↓
AI Processing
    ↓
Damage Detection
    ↓
Human Review
    ↓
Damage Confirmation
    ↓
Road Health Update
    ↓
Maintenance Creation
    ↓
Contractor Assignment
    ↓
Maintenance Completion
    ↓
Repair Evidence
    ↓
AI Verification
    ↓
Human Verification
    ↓
Later Inspection
    ↓
Recurrence Detection
    ↓
Historical Road Intelligence
```

---

# 21.2 Role Validation

Repeat relevant workflows for:

```text
Administrator
Road Authority
Field Inspector
Contractor
```

Verify that unauthorized operations fail.

---

# 21.3 Data Integrity Validation

Verify:

```text
WHO
WHAT
WHERE
WHEN
EVIDENCE
AI MODEL/VERSION
HUMAN REVIEW
MAINTENANCE
REPAIR EVIDENCE
VERIFICATION
RECURRENCE
```

remain traceable.

---

# 22. Phase 18 — Production Release

## Objective

Deploy the validated system.

---

# 22.1 Release Order

Recommended sequence:

```text
Database
    ↓
Redis
    ↓
AI Worker
    ↓
FastAPI
    ↓
Nginx
    ↓
Web
    ↓
Android Release
```

---

# 22.2 Production Smoke Test

Immediately after deployment:

### API

```text
GET /health/live
GET /health/ready
```

### Authentication

```text
Login
Logout
Token refresh
```

### Web

```text
Login
Dashboard
Road
Map
Damage
Maintenance
```

### Android

```text
Login
Camera
GPS
Inspection
Offline queue
Sync
```

### AI

```text
Submit test media
Process
Verify persisted result
```

---

# 23. Recommended Implementation Order by Dependency

The coding agent should follow this simplified order:

```text
01. Repository
        ↓
02. Environment
        ↓
03. Docker
        ↓
04. FastAPI foundation
        ↓
05. PostgreSQL/PostGIS
        ↓
06. Alembic
        ↓
07. Authentication
        ↓
08. RBAC
        ↓
09. Organizations
        ↓
10. Roads
        ↓
11. Road segments
        ↓
12. Inspections
        ↓
13. Media storage
        ↓
14. Processing jobs
        ↓
15. Redis/Celery
        ↓
16. AI model registry
        ↓
17. YOLO inference
        ↓
18. Damage records
        ↓
19. Human review
        ↓
20. Web application shell
        ↓
21. Dashboard
        ↓
22. Road/segment UI
        ↓
23. Inspection UI
        ↓
24. AI review UI
        ↓
25. GIS
        ↓
26. Road health
        ↓
27. Maintenance
        ↓
28. Repair evidence
        ↓
29. Repair verification
        ↓
30. Recurrence
        ↓
31. Android foundation
        ↓
32. Android inspection
        ↓
33. Offline synchronization
        ↓
34. Prediction
        ↓
35. Analytics
        ↓
36. Reports
        ↓
37. Security hardening
        ↓
38. Performance testing
        ↓
39. Full E2E testing
        ↓
40. Production deployment
```

---

# 24. Parallel Development Opportunities

Some work can happen in parallel once their dependencies are stable.

## Backend + Web

After API contracts stabilize:

```text
Backend API
        +
Web UI
```

can proceed in parallel.

---

## Backend + Android

After inspection and upload APIs stabilize:

```text
Backend
        +
Android
```

can proceed in parallel.

---

## AI + Web Review

Once the AI output contract is defined:

```text
AI Worker
        +
AI Review UI
```

can proceed in parallel.

---

## Testing

Testing should begin with implementation rather than being postponed until the end.

```text
Feature
→ Unit Tests
→ Integration Tests
→ Client Tests
→ E2E Coverage
```

---

# 25. MVP Boundary

The first production-capable MVP MUST include:

## Platform

- authentication
- organization management
- RBAC
- audit logging
- PostgreSQL/PostGIS
- Supabase Storage

## Road

- roads
- road segments
- GIS

## Inspection

- Android authentication
- camera
- GPS
- inspection creation
- offline queue
- synchronization
- media upload

## AI

- YOLO inference
- initial damage classes
- confidence
- severity
- model versioning
- AI processing jobs

## Human Review

- AI result review
- confirmation
- rejection
- correction

## Maintenance

- maintenance jobs
- assignment
- status lifecycle
- repair evidence

## Verification

- AI verification
- human verification

## Intelligence

- road health
- basic analytics
- historical records
- recurrence foundation

## Deployment

- Docker Compose
- VPS
- Nginx
- Vercel
- Supabase
- HTTPS
- CI/CD

---

# 26. Features Explicitly Deferred From MVP

The following must NOT delay the initial implementation:

```text
Advanced video analytics
Dedicated GPU infrastructure
Multi-GPU orchestration
Traffic API integration
Weather API integration
Citizen reporting
Government API integrations
Advanced route optimization
Advanced push notification infrastructure
Multi-city enterprise scaling
Advanced deep-learning deterioration models
Automatic road construction planning
Fully autonomous maintenance decisions
```

These can be added after the core lifecycle is stable.

---

# 27. Data Availability Strategy

The project has a critical dependency on real historical data for prediction.

Therefore:

```text
Operational Platform
        ↓
Data Collection
        ↓
Validated Historical Dataset
        ↓
Feature Engineering
        ↓
Model Training
        ↓
Model Validation
        ↓
Prediction Deployment
```

The coding agent MUST NOT reverse this order.

If the dataset is insufficient:

```text
Prediction = NOT AVAILABLE
```

is preferable to fabricated or meaningless predictions.

---

# 28. AI Dataset Roadmap

## Stage 1 — Dataset Preparation

Collect:

```text
road images
potholes
cracks
depressions
waterlogging
surface damage
other
```

---

## Stage 2 — Annotation

Use consistent bounding-box annotations.

Validate:

- class labels
- bounding boxes
- duplicates
- corrupt images
- ambiguous images
- class imbalance

---

## Stage 3 — Dataset Versioning

Example:

```text
dataset-v1
dataset-v2
dataset-v3
```

Every training run must identify its dataset version.

---

## Stage 4 — YOLO Training

Record:

```text
dataset version
training configuration
model architecture
hyperparameters
metrics
artifact
```

---

## Stage 5 — Validation

Measure:

```text
precision
recall
per-class AP
mAP@0.5
mAP@0.5:0.95
```

---

## Stage 6 — Deployment

Only validated models may enter:

```text
APPROVED
→ DEPLOYED
```

---

# 29. Prediction Model Roadmap

## Stage 1

Collect road history.

## Stage 2

Define prediction target.

## Stage 3

Generate features.

## Stage 4

Create time-aware dataset.

## Stage 5

Train XGBoost.

## Stage 6

Evaluate.

## Stage 7

Register model.

## Stage 8

Deploy inference.

## Stage 9

Monitor prediction quality.

## Stage 10

Retrain using controlled datasets.

---

# 30. Release Milestones

## Milestone M0 — Architecture Ready

Criteria:

- documents approved
- repository initialized
- architecture locked
- stack locked

---

## Milestone M1 — Platform Foundation

Criteria:

- API
- database
- migrations
- authentication
- RBAC
- organizations

---

## Milestone M2 — Road Intelligence

Criteria:

- roads
- segments
- GIS
- inspections
- media

---

## Milestone M3 — AI Intelligence

Criteria:

- processing jobs
- YOLO
- detection
- severity
- model registry
- human review

---

## Milestone M4 — Operational Management

Criteria:

- maintenance
- repair evidence
- verification
- road health

---

## Milestone M5 — Field Application

Criteria:

- Android
- camera
- GPS
- offline mode
- synchronization

---

## Milestone M6 — Predictive Intelligence

Criteria:

- validated dataset
- XGBoost
- prediction API
- prediction UI
- model versioning

---

## Milestone M7 — Historical Intelligence

Criteria:

- recurrence
- historical analysis
- analytics
- reports

---

## Milestone M8 — Production Ready

Criteria:

- security testing
- performance testing
- reliability testing
- E2E testing
- deployment validation
- backup/restore validation

---

# 31. Feature Completion Standard

A roadmap item is NOT complete when the code merely exists.

A feature is complete only when:

```text
Requirement
    ↓
Design
    ↓
Database
    ↓
API
    ↓
Authorization
    ↓
Implementation
    ↓
Validation
    ↓
Error Handling
    ↓
State Handling
    ↓
Testing
    ↓
Observability
    ↓
Documentation
```

For AI features:

```text
Model
    ↓
Model Version
    ↓
Inference
    ↓
Persistence
    ↓
Evaluation
    ↓
Human Review
    ↓
Auditability
```

---

# 32. Coding-Agent Execution Rules

The coding agent MUST:

1. Read all approved documentation before major implementation.
2. Follow this roadmap.
3. Never invent a competing architecture.
4. Never replace PostgreSQL/PostGIS with another primary database.
5. Never replace FastAPI with another backend framework.
6. Never introduce external generative AI APIs.
7. Never expose service-role credentials to clients.
8. Never allow clients to access PostgreSQL directly.
9. Never fabricate AI results.
10. Never silently overwrite historical records.
11. Preserve model version information.
12. Preserve original AI detections after human review.
13. Implement organization isolation.
14. Implement authorization server-side.
15. Use migrations for database changes.
16. Add tests with every meaningful feature.
17. Implement failure states explicitly.
18. Use real APIs rather than hardcoded UI data.
19. Keep modules loosely coupled.
20. Document approved architecture changes.
21. Never remove functionality merely to make tests pass.
22. Never bypass validation to make a demo appear successful.
23. Never commit secrets.
24. Keep production and development configuration separate.
25. Preserve backwards compatibility for existing API contracts unless an approved breaking change is made.

---

# 33. Architecture Change Process

If implementation reveals that an architectural change is required:

```text
Identify Problem
      ↓
Document Current Behavior
      ↓
Explain Proposed Change
      ↓
Assess Dependencies
      ↓
Update Relevant Specification
      ↓
Update This Roadmap
      ↓
Implement
      ↓
Test
```

The coding agent MUST NOT silently change architecture.

---

# 34. Definition of Roadmap Completion

The roadmap is complete when:

- all MVP phases are implemented
- all required API contracts are implemented
- web workflow works
- Android field workflow works
- offline synchronization works
- AI processing works
- human review works
- road health works
- maintenance lifecycle works
- repair verification works
- recurrence tracking works
- analytics works
- security validation passes
- E2E lifecycle passes
- production deployment succeeds
- backup/recovery is validated
- documentation reflects the final implementation

---

# 35. Final System Lifecycle

The final implementation must preserve the complete chain:

```text
FIELD OBSERVATION
        ↓
INSPECTION
        ↓
MEDIA / GPS EVIDENCE
        ↓
AI PROCESSING
        ↓
DAMAGE DETECTION
        ↓
DAMAGE CLASSIFICATION
        ↓
SEVERITY ASSESSMENT
        ↓
HUMAN REVIEW
        ↓
ROAD / SEGMENT ASSOCIATION
        ↓
ROAD HEALTH
        ↓
DETERIORATION PREDICTION
        ↓
MAINTENANCE PRIORITY
        ↓
MAINTENANCE JOB
        ↓
REPAIR
        ↓
REPAIR EVIDENCE
        ↓
AI VERIFICATION
        ↓
HUMAN VERIFICATION
        ↓
HISTORICAL RECORD
        ↓
RECURRENCE MONITORING
        ↓
HISTORICAL ROAD INTELLIGENCE
        ↓
FUTURE MAINTENANCE DECISIONS
```

---

# 36. Final Implementation Principle

The platform is not merely a pothole detection application.

It is a:

> **Road Intelligence → Maintenance → Verification → Recurrence Management System.**

The implementation roadmap therefore prioritizes the complete evidence lifecycle over isolated AI features.

The final system must allow an authorized organization to answer:

```text
What damage was found?
        ↓
Where was it found?
        ↓
When was it found?
        ↓
Who observed it?
        ↓
What did the AI detect?
        ↓
Which model/version produced it?
        ↓
Was it human-reviewed?
        ↓
What road segment is affected?
        ↓
How healthy is that segment?
        ↓
Is deterioration predicted?
        ↓
What maintenance action was taken?
        ↓
Who performed it?
        ↓
What evidence proves the repair?
        ↓
Was the repair verified?
        ↓
Did the damage recur?
        ↓
What does the historical record tell us?
```

This chain is the primary implementation objective of the entire platform.

---

# 37. Final Roadmap Acceptance Checklist

Before implementation begins:

- [x] Product context approved
- [x] PRD approved
- [x] SRS approved
- [x] System architecture approved
- [x] Technology stack approved
- [x] Database schema approved
- [x] API specification approved
- [x] AI/ML specification approved
- [x] RBAC specification approved
- [x] UI/UX specification approved
- [x] Android specification approved
- [x] Security specification approved
- [x] Deployment specification approved
- [x] Testing strategy approved
- [x] Implementation roadmap approved

The next implementation document is:

```text
16_CHANGELOG.md
```

which will establish the controlled record for specification and architecture changes throughout development.