# PROJECT_CONTEXT.md

**Project Name:** Road Intelligence & Pothole Management Platform  
**Project Type:** Full-Stack AI/ML Road Infrastructure Intelligence System  
**Document Status:** Master Project Context / Source of Truth  
**Version:** 1.0  
**Last Updated:** October 2026

---

# 1. Project Overview

The Road Intelligence & Pothole Management Platform is an end-to-end road-condition monitoring and maintenance intelligence system designed to detect road damage, assess its severity, identify affected road segments, predict deterioration, prioritize maintenance, verify completed repairs, and monitor recurrence.

The platform is intentionally designed to be more than a basic pothole detector.

The complete lifecycle is:

```text
Road Data Collection
        ↓
AI Road Damage Detection
        ↓
Damage Classification
        ↓
Severity Assessment
        ↓
GPS / GIS Mapping
        ↓
Road Segment Association
        ↓
Road Health Assessment
        ↓
Deterioration Prediction
        ↓
Maintenance Priority
        ↓
Maintenance / Repair
        ↓
AI Repair Verification
        ↓
Recurrence Monitoring
        ↓
Historical Road Intelligence
```

The system should provide actionable information to road authorities, inspectors, and maintenance teams rather than simply displaying detected potholes.

---

# 2. Core Problem

Road damage is often identified through manual inspection, citizen complaints, periodic surveys, or disconnected reporting systems.

This creates several problems:

- Damage can remain undocumented for long periods.
- Manual inspection is time-consuming.
- Different road issues may be recorded inconsistently.
- Authorities may not have a unified geographical view of road conditions.
- Maintenance decisions may not account for severity, traffic relevance, or historical deterioration.
- Completed repairs may not be independently verified.
- Repaired locations may deteriorate again without being tracked.
- Historical road-condition data may not be effectively used for prediction.

This platform addresses these problems through automated computer vision, geospatial data, structured maintenance records, and machine-learning-based prediction.

---

# 3. Product Vision

Create a unified digital platform that converts road-condition observations into structured and actionable road-maintenance intelligence.

The system should answer:

1. Where is the damage?
2. What type of damage is present?
3. How severe is it?
4. Which road segment is affected?
5. What is the current health of that road?
6. Which roads require attention?
7. Which roads are likely to deteriorate?
8. Was the reported repair actually completed?
9. Did the repaired location deteriorate again?
10. What historical evidence exists for that road segment?

---

# 4. Product Scope

## 4.1 Primary Scope

The first complete version of the platform will support:

- User authentication and authorization
- Road-condition data collection
- Image/video upload
- GPS/location capture
- AI-based road-damage detection
- Damage classification
- Damage severity estimation
- Geographic visualization
- Road-segment association
- Road health scoring
- Maintenance priority calculation
- Deterioration prediction
- Maintenance/repair workflow
- Before/after repair verification
- Recurrence tracking
- Historical records
- Analytics dashboard
- Reports
- Role-based access control

---

# 5. Road Damage Types

The detection architecture should be extensible.

The initial system should support these damage categories where sufficient training data is available:

- Pothole
- Crack
- Depression
- Waterlogging
- Surface damage
- Other detectable road-surface damage

The architecture must NOT hard-code the system around potholes only.

New damage classes should be addable through model configuration and database metadata rather than requiring a complete application rewrite.

---

# 6. Primary Users

The platform should support role-based access.

## 6.1 Administrator

Responsible for:

- Managing users
- Managing authorities/organizations
- Managing system configuration
- Viewing all road intelligence
- Managing access permissions
- Monitoring system activity

## 6.2 Road Authority / Municipal Official

Responsible for:

- Monitoring road conditions
- Reviewing detected damage
- Viewing road-health information
- Reviewing maintenance priorities
- Creating/assigning maintenance work
- Monitoring repair status
- Reviewing repair verification
- Viewing historical analytics

## 6.3 Field Inspector

Responsible for:

- Capturing road images/video
- Recording GPS information
- Performing inspections
- Reviewing assigned inspection tasks
- Submitting inspection data
- Capturing post-repair evidence

## 6.4 Maintenance/Contractor Role

Responsible for:

- Viewing assigned maintenance work
- Updating work status
- Submitting repair evidence
- Providing completion information

The exact permission matrix will be defined in `USER_ROLES_PERMISSIONS.md`.

---

# 7. System Interfaces

The system consists of three major application interfaces.

## 7.1 Web Application

Primary interface for:

- Administrators
- Road authorities
- Inspectors
- Maintenance management

Technology:

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts
- Leaflet

The web application will provide dashboards, maps, analytics, road records, maintenance workflows, and administrative functionality.

---

# 8. Android Field Application

The Android application is a field-data-collection client, not the primary system interface.

Technology:

- Kotlin
- Jetpack Compose
- Android Camera APIs
- Android Location APIs

Primary capabilities:

- User authentication
- Camera capture
- Image/video capture
- GPS capture
- Road inspection
- Detection submission
- Inspection history
- Assigned work
- Post-repair evidence capture
- Basic offline data queueing where required

The Android application communicates with the FastAPI backend through HTTPS REST APIs.

---

# 9. Backend

The backend is the central application and intelligence gateway.

Technology:

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication
- Role-based authorization

The backend is responsible for:

- Authentication
- Authorization
- API routing
- Data validation
- Business logic
- Road/damage management
- Inspection management
- Maintenance workflow
- AI job orchestration
- Prediction workflow
- Database interaction
- File metadata management
- Audit logging

The backend must NOT expose database credentials, AI model internals, or privileged operations directly to clients.

---

# 10. AI/ML Architecture

The project uses locally hosted AI/ML models.

## 10.1 Computer Vision

Primary technology:

- YOLO
- PyTorch
- OpenCV

The detection pipeline should support:

```text
Input Image / Video
        ↓
Preprocessing
        ↓
YOLO Detection
        ↓
Damage Class
        ↓
Bounding Box
        ↓
Confidence
        ↓
Severity Analysis
        ↓
Structured Damage Record
```

The exact YOLO model version will be finalized in `AI_ML_SPECIFICATION.md` based on dataset compatibility, accuracy, inference requirements, and deployment constraints.

## 10.2 Prediction

Technology:

- XGBoost
- scikit-learn
- Pandas
- NumPy

Prediction inputs may include:

- Historical damage
- Damage severity
- Damage frequency
- Road segment history
- Repair history
- Time since repair
- Inspection frequency
- Road-condition metrics
- Available environmental/traffic-related data

The prediction model must be trained and evaluated using documented datasets and metrics.

---

# 11. No External AI API Dependency

The core AI system should not depend on external generative-AI APIs.

Detection and prediction should run using our own deployed models:

```text
YOLO
OpenCV
PyTorch
XGBoost
scikit-learn
```

The backend must not require services such as OpenAI, Gemini, Claude, or similar external AI APIs for the core pothole detection and prediction functionality.

This ensures:

- Predictable operation
- Greater control over data
- Reduced third-party dependency
- Easier reproducibility
- Better control over inference costs

---

# 12. GIS / Mapping

The platform requires geographic visualization.

Primary technologies:

- Leaflet
- OpenStreetMap

The system should support:

- Damage markers
- Road-segment visualization
- Severity-based visualization
- Road-health visualization
- Maintenance-priority visualization
- Inspection locations
- Repair locations
- Recurrence locations

GPS data should be stored with appropriate accuracy metadata when available.

---

# 13. Database

Primary database:

**PostgreSQL**

The database stores structured application data including:

- Users
- Roles
- Organizations
- Roads
- Road segments
- Inspections
- Damage detections
- Damage classifications
- Severity information
- Locations
- Maintenance jobs
- Repairs
- Verification results
- Prediction results
- Audit logs

The database schema will be formally defined in:

`DATABASE_SCHEMA.md`

---

# 14. Storage

Large media files such as:

- Road images
- Inspection videos
- Before-repair images
- After-repair images
- Evidence files

must not be stored directly inside normal PostgreSQL records.

The system should use object/file storage.

Initial storage:

**Supabase Storage**

PostgreSQL stores metadata and references to stored objects.

Example:

```text
PostgreSQL
    │
    ├── image_id
    ├── inspection_id
    ├── storage_path
    ├── uploaded_at
    └── metadata
             │
             ▼
       Object Storage
          Image/Video
```

---

# 15. Authentication

Authentication will use:

- JWT
- Secure password hashing
- Role-based access control

The frontend and Android application must communicate with the backend through authenticated APIs.

Sensitive credentials must never be stored in source code.

Environment variables must be used for:

- Database credentials
- JWT secrets
- Storage credentials
- Deployment secrets
- Other sensitive configuration

---

# 16. Deployment Architecture

The initial deployment should prioritize simplicity.

## 16.1 Web Frontend

Deploy:

**Next.js → Vercel**

The web frontend communicates with the backend through HTTPS.

## 16.2 Backend and AI

Deploy:

**FastAPI + AI workers → VPS using Docker Compose**

The initial server will contain containers for services such as:

```text
VPS
│
├── Nginx
├── FastAPI
├── AI Worker
├── Redis
└── Supporting services
```

## 16.3 Database

Use:

**Supabase PostgreSQL**

## 16.4 Object Storage

Use:

**Supabase Storage**

## 16.5 Android

The Android application will be distributed initially as an APK for development/testing.

Google Play deployment can be performed later.

---

# 17. Deployment Flow

```text
                         INTERNET
                             │
               ┌─────────────┴─────────────┐
               │                           │
          Next.js Web                 Android App
           on Vercel                       │
               │                           │
               └─────────────┬─────────────┘
                             │
                           HTTPS
                             │
                             ▼
                       Nginx / VPS
                             │
                             ▼
                       FastAPI API
                             │
                 ┌───────────┼───────────┐
                 │           │           │
                 ▼           ▼           ▼
             PostgreSQL   AI Worker    Redis
             Supabase     YOLO/XGB
                 │
                 ▼
          Supabase Storage
```

The architecture must allow the AI processing infrastructure to be moved to a dedicated GPU server later without requiring major frontend or database changes.

---

# 18. Docker Architecture

Docker is used to make the backend infrastructure reproducible.

The backend deployment should be managed using Docker Compose.

Conceptually:

```text
docker-compose.yml

services:
    nginx
    api
    ai-worker
    redis
```

The exact production configuration will be defined in `DEPLOYMENT.md`.

The project should not rely on manually installing application dependencies on the production server.

---

# 19. Core Data Flow

## 19.1 Field Inspection

```text
Inspector
    ↓
Android Camera
    ↓
Image + GPS
    ↓
FastAPI
    ↓
Object Storage
    ↓
AI Processing
    ↓
YOLO
    ↓
Damage Detection
    ↓
Severity Analysis
    ↓
PostgreSQL
    ↓
Road Health / Priority
    ↓
Web Dashboard
```

## 19.2 Repair Verification

```text
Before Repair
      ↓
Damage Record
      ↓
Maintenance Assignment
      ↓
Repair
      ↓
After Repair Image
      ↓
AI Verification
      ↓
Verification Result
      ↓
Maintenance Record Updated
```

## 19.3 Recurrence

```text
Historical Damage
       +
Repair Record
       +
New Inspection
       ↓
Same Road Segment
       ↓
Compare Historical State
       ↓
Potential Recurrence
       ↓
Recurrence Record
```

---

# 20. Road Segment Concept

The system should not treat every pothole as an isolated object.

Damage should be associated with a road segment whenever sufficient geographic information is available.

Conceptually:

```text
Road
 │
 ├── Segment A
 │     ├── Damage 1
 │     ├── Damage 2
 │     └── Repair
 │
 ├── Segment B
 │     ├── Damage 3
 │     └── Damage 4
 │
 └── Segment C
       └── No current damage
```

This enables road-level analytics and deterioration tracking.

---

# 21. Road Health

The platform should calculate a structured road-health indicator using measurable factors rather than an arbitrary manually assigned value.

Potential inputs include:

- Damage count
- Damage severity
- Damage density
- Recurrence
- Recent repair history
- Age of unresolved damage
- Historical deterioration
- Other validated road-condition indicators

The exact formula and weighting must be documented in the AI/analytics specification.

The system must retain the underlying factors used to produce a score so that the result is explainable.

---

# 22. Maintenance Priority

Maintenance priority should be calculated from explicit measurable factors.

Potential factors:

- Severity
- Number of affected locations
- Road health
- Damage age
- Recurrence
- Road-segment importance
- Available traffic/usage data
- Safety-related indicators

The system must expose the factors contributing to the priority rather than returning only an unexplained number.

---

# 23. Deterioration Prediction

The predictive system is intended to estimate future road-condition deterioration.

It should not present predictions as guaranteed outcomes.

The system should provide:

- Prediction value
- Prediction horizon
- Model version
- Relevant input features
- Confidence/uncertainty information where supported
- Timestamp
- Data/model version used

---

# 24. Explainability

AI-generated results should be understandable to users.

For every major AI result, where practical, the system should expose supporting information.

Example:

```text
Maintenance Priority: HIGH

Contributing factors:
- Severe potholes detected
- Multiple unresolved detections
- Recent recurrence
- Poor road-health indicators
```

The system should avoid unexplained AI decisions wherever a meaningful explanation can be provided.

---

# 25. Auditability

The platform should maintain important historical records.

Examples:

- Who created an inspection?
- Who reviewed a detection?
- Who assigned maintenance?
- Who changed maintenance status?
- Who submitted repair evidence?
- When was repair verification performed?
- Which AI model generated a result?

Important state changes should be recorded in audit logs.

---

# 26. Data Integrity Rules

The system must:

- Validate incoming data.
- Validate uploaded file types and sizes.
- Validate GPS coordinates.
- Validate user permissions.
- Prevent unauthorized record modification.
- Maintain timestamps.
- Maintain relationships between inspections, detections, repairs, and road segments.
- Avoid silently overwriting historical records.
- Preserve model/version metadata for AI-generated results.

---

# 27. Offline Considerations

Field environments may have unreliable connectivity.

The Android application should be architected so that inspection data can be temporarily queued locally when connectivity is unavailable.

Conceptually:

```text
Capture
   ↓
Local Queue
   ↓
Internet Available?
   ├── No → Keep locally
   │
   └── Yes → Upload
```

The first implementation should prioritize reliable synchronization rather than attempting to make the complete AI system offline.

---

# 28. Frontend Design Direction

The web application should have a professional civic-tech / infrastructure intelligence appearance.

The interface should prioritize:

- Clear information hierarchy
- Maps
- Analytics
- Status indicators
- Road health
- Maintenance workflow
- Detection evidence
- Responsive design
- Accessibility

The UI should avoid looking like a generic AI dashboard.

Primary visual elements should communicate:

```text
Road Condition
Damage
Severity
Location
Priority
Maintenance
Verification
Recurrence
```

The detailed visual system will be defined in `UI_UX_SPECIFICATION.md`.

---

# 29. Engineering Principles

All implementation generated from this document must follow these principles.

### 29.1 Modular Architecture

Frontend, backend, AI processing, database, and Android should have clear boundaries.

### 29.2 API-First Backend

The backend should expose documented REST APIs consumed by both web and Android clients.

### 29.3 Strong Validation

Use Pydantic/Zod and server-side validation.

### 29.4 Type Safety

Use TypeScript on the frontend and typed Python models/schemas on the backend.

### 29.5 Security by Default

Never expose secrets or privileged database operations to clients.

### 29.6 Explainable Intelligence

AI results should retain evidence and supporting metadata.

### 29.7 Reproducibility

AI predictions must record model/version information.

### 29.8 Maintainability

Avoid tightly coupling frontend components directly to database structures.

### 29.9 Extensibility

New damage classes, models, road metrics, and user roles should be addable without rewriting the entire application.

### 29.10 Production-Oriented Development

Development code should be structured so it can eventually be deployed without a major rewrite.

---

# 30. Development Environment

Recommended development environment:

```text
Operating System
        ↓
Git
        ↓
Docker / Docker Compose
        ↓
Frontend
Next.js + TypeScript
        +
Backend
FastAPI + Python
        +
AI
PyTorch + YOLO + OpenCV
        +
Database
PostgreSQL
```

The development environment should closely resemble production wherever practical.

---

# 31. Repository Structure

The project should use a clear monorepo structure.

Initial target:

```text
road-intelligence-platform/
│
├── apps/
│   ├── web/
│   └── android/
│
├── services/
│   ├── api/
│   └── ai-worker/
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

The exact structure may be refined in the architecture document, but the separation between web, mobile, API, AI, and infrastructure must remain clear.

---

# 32. Environment Separation

The project should support at least:

```text
Development
     ↓
Staging
     ↓
Production
```

Environment-specific configuration must not be hard-coded.

Use:

```text
.env.example
.env.development
.env.production
```

Actual secrets must never be committed to Git.

---

# 33. Testing Requirements

Testing must cover:

### Frontend
- Components
- Forms
- API integration
- Authentication
- Critical user flows

### Backend
- Unit tests
- API tests
- Authentication tests
- Authorization tests
- Database integration tests

### AI
- Detection accuracy
- Precision
- Recall
- mAP
- Inference performance
- Classification performance

### Prediction
- MAE/RMSE where appropriate
- R² where appropriate
- Cross-validation
- Dataset leakage checks

### End-to-End
- Capture → upload → detection
- Detection → road segment
- Detection → maintenance
- Repair → verification
- Recurrence workflow

---

# 34. Non-Goals for the Initial Version

The initial implementation should NOT attempt to build everything possible.

The following should remain outside the initial core scope unless explicitly added later:

- Autonomous vehicle control
- Automated road repair machinery
- Real-time city-wide traffic control
- Fully autonomous government decision-making
- Guaranteed prediction of future potholes
- Direct integration with every municipal government system
- Mandatory dependence on external generative AI APIs

The platform provides intelligence and workflow support; humans remain responsible for operational decisions.

---

# 35. Initial Product Success Criteria

The first production-capable version should demonstrate the complete pipeline:

```text
Capture
   ↓
Upload
   ↓
Detect
   ↓
Classify
   ↓
Assess Severity
   ↓
Map
   ↓
Associate with Road Segment
   ↓
Calculate Road Health
   ↓
Prioritize Maintenance
   ↓
Create Maintenance Record
   ↓
Submit Repair Evidence
   ↓
Verify Repair
   ↓
Track Recurrence
```

A feature should not be considered complete merely because a UI screen exists.

A feature is complete when:

```text
UI
 +
API
 +
Database
 +
Business Logic
 +
Validation
 +
Error Handling
 +
Testing
```

are implemented as required.

---

# 36. Coding-Agent Rules

Any coding agent working on this project must follow these rules.

### Rule 1 — Read the documentation first

Before implementing a feature, read the relevant project documents.

### Rule 2 — Do not invent architecture

Do not introduce a new framework, database, authentication system, AI provider, or deployment architecture without updating the specification.

### Rule 3 — Preserve existing contracts

Do not silently change API contracts or database structures used by other modules.

### Rule 4 — No fake functionality

Do not create UI buttons that only display success messages without implementing the underlying operation.

### Rule 5 — No hard-coded production data

Demo/seed data must be clearly separated from production data.

### Rule 6 — No secrets in source code

Use environment variables.

### Rule 7 — Validate server-side

Never rely exclusively on frontend validation.

### Rule 8 — Handle failures explicitly

API, AI, storage, database, network, and authentication failures must produce meaningful errors.

### Rule 9 — Document architectural changes

If implementation requires changing an agreed architectural decision, update the appropriate documentation before proceeding.

### Rule 10 — Keep the system modular

Do not solve a local problem by introducing unnecessary coupling between unrelated modules.

---

# 37. Source-of-Truth Hierarchy

When documents contain conflicting information, use this hierarchy:

```text
1. Latest approved architecture decision
2. PROJECT_CONTEXT.md
3. SYSTEM_ARCHITECTURE.md
4. SRS.md
5. PRD.md
6. Module-specific specifications
7. Existing implementation
```

However, if an existing implementation conflicts with the approved specification, the agent must identify the conflict instead of silently choosing one.

---

# 38. Documentation Set

This master document will be followed by:

```text
01_PROJECT_CONTEXT.md
02_PRD.md
03_SRS.md
04_SYSTEM_ARCHITECTURE.md
05_TECH_STACK.md
06_DATABASE_SCHEMA.md
07_API_SPECIFICATION.md
08_AI_ML_SPECIFICATION.md
09_USER_ROLES_PERMISSIONS.md
10_UI_UX_SPECIFICATION.md
11_ANDROID_APP_SPEC.md
12_SECURITY.md
13_DEPLOYMENT.md
14_TESTING_STRATEGY.md
15_ROADMAP.md
16_CHANGELOG.md
```

The numbering is organizational; the documents must remain internally consistent.

---

# 39. Final Architectural Decision

The approved high-level architecture is:

```text
                    ┌───────────────────┐
                    │   Web Application │
                    │ Next.js / Vercel │
                    └─────────┬─────────┘
                              │
                              │ HTTPS REST
                              │
┌─────────────────┐           ▼
│ Android App     │──────► FastAPI Backend
│ Kotlin/Compose  │           │
└─────────────────┘           │
                              ├───────────────┐
                              │               │
                              ▼               ▼
                         AI Processing     Business Logic
                         YOLO/OpenCV       Auth/RBAC
                         XGBoost           Workflows
                              │               │
                              └───────┬───────┘
                                      │
                       ┌──────────────┴──────────────┐
                       ▼                             ▼
                 PostgreSQL                    Object Storage
                  Supabase                     Supabase Storage
                       │
                       ▼
                Road Intelligence
                 & Analytics
```

Backend infrastructure is containerized with Docker and deployed initially on a VPS.

The architecture must remain modular so that AI processing can later be moved to dedicated GPU infrastructure without redesigning the complete application.

---

# 40. Master Principle

The platform is not simply a pothole detector.

It is a:

**Road Intelligence → Maintenance → Verification → Recurrence Management System**

The AI identifies and analyzes road conditions.

The platform organizes the information.

The maintenance workflow tracks actions.

The verification system checks outcomes.

The historical system learns from previous road conditions.

The final system should therefore connect **detection, geography, prediction, maintenance, verification, and historical intelligence** into one coherent platform.