# SRS.md

# Road Intelligence & Pothole Management Platform

**Project Name:** Road Intelligence & Pothole Management Platform  
**Document Type:** Software Requirements Specification  
**Version:** 1.0  
**Status:** Approved for Architecture & Implementation  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`  
**Last Updated:** October 2026

---

# 1. Purpose

This Software Requirements Specification defines the technical and behavioral requirements of the Road Intelligence & Pothole Management Platform.

It converts the product requirements into software-level requirements that can be implemented and tested by:

- Frontend developers
- Backend developers
- Android developers
- AI/ML developers
- Database developers
- DevOps engineers
- QA engineers
- Coding agents

This document is intended to eliminate ambiguity before implementation begins.

---

# 2. Scope

The system shall provide an integrated platform for:

1. User authentication
2. Role-based authorization
3. Road management
4. Road-segment management
5. Field inspections
6. Image/video ingestion
7. AI road-damage detection
8. Damage classification
9. Severity assessment
10. GIS visualization
11. Road-health calculation
12. Deterioration prediction
13. Maintenance management
14. Repair evidence collection
15. AI-assisted repair verification
16. Recurrence tracking
17. Analytics
18. Reports
19. Notifications
20. Audit logging
21. Android offline inspection synchronization
22. Dockerized deployment

---

# 3. System Context

The system consists of:

```text
                    ┌──────────────────────┐
                    │      Web Client      │
                    │ Next.js + TypeScript │
                    └──────────┬───────────┘
                               │
                               │ HTTPS REST
                               │
┌──────────────────────┐       ▼
│ Android Field Client │──── FastAPI Backend
│ Kotlin + Compose     │       │
└──────────────────────┘       │
                               ├─────────────┐
                               │             │
                               ▼             ▼
                         PostgreSQL      AI Workers
                         Supabase        YOLO/XGBoost
                               │             │
                               └──────┬──────┘
                                      │
                                      ▼
                              Object Storage
```

---

# 4. Architectural Constraints

The implementation shall follow these constraints.

## ARC-001

The backend shall use FastAPI and Python.

## ARC-002

The primary relational database shall be PostgreSQL.

## ARC-003

The web client shall use Next.js and TypeScript.

## ARC-004

The Android client shall use Kotlin and Jetpack Compose.

## ARC-005

Core computer-vision inference shall use locally deployed models.

## ARC-006

Core prediction shall use XGBoost/scikit-learn where sufficient data exists.

## ARC-007

The system shall not require OpenAI, Gemini, Claude, or another external generative-AI API for core functionality.

## ARC-008

Large media shall use object storage rather than PostgreSQL binary fields.

## ARC-009

Long-running AI operations shall not unnecessarily block normal API requests.

## ARC-010

Backend infrastructure shall be containerized using Docker.

## ARC-011

The backend architecture shall permit AI workers to be moved to a dedicated GPU machine later.

---

# 5. Actors

## ACT-001 — Administrator

Full administrative access subject to security policies.

## ACT-002 — Authority

Access to road intelligence, inspections, maintenance, analytics, and authorized administrative operations.

## ACT-003 — Inspector

Access to field inspections, assigned tasks, inspection history, and evidence submission.

## ACT-004 — Contractor

Access to assigned maintenance jobs and repair evidence workflows.

## ACT-005 — AI Worker

Non-human service responsible for asynchronous model execution.

## ACT-006 — Background Worker

Non-human service responsible for asynchronous jobs such as processing, synchronization, or notification tasks.

---

# 6. System Modules

The software shall be logically divided into:

```text
Authentication
User Management
Organization Management
Road Management
Road Segment Management
Inspection Management
Media Management
Damage Management
AI Detection
Severity Engine
GIS
Road Health Engine
Prediction Engine
Maintenance Management
Repair Evidence
Verification Engine
Recurrence Engine
Analytics
Reports
Notifications
Audit Logging
Background Jobs
System Administration
```

---

# 7. Authentication Requirements

## AUTH-001

The system shall allow an authorized user to log in using email and password.

## AUTH-002

Passwords shall never be stored in plaintext.

## AUTH-003

Authentication credentials shall be transmitted only over HTTPS in production.

## AUTH-004

Authentication tokens shall have an expiration mechanism.

## AUTH-005

Expired or invalid tokens shall be rejected.

## AUTH-006

Authentication endpoints shall implement appropriate rate limiting.

## AUTH-007

Sensitive authentication errors shall not reveal whether unnecessary internal information exists.

## AUTH-008

Logout shall invalidate or otherwise terminate the client authentication session according to the chosen token strategy.

## AUTH-009

Authentication state shall be handled consistently across the web and Android applications.

---

# 8. Authorization Requirements

## AUTHZ-001

Every protected API endpoint shall perform server-side authorization.

## AUTHZ-002

Frontend route restrictions shall not be considered a security boundary.

## AUTHZ-003

A user shall only access resources permitted by their role and organization scope.

## AUTHZ-004

An inspector shall not be able to modify administrative configuration.

## AUTHZ-005

A contractor shall only access maintenance work permitted by assignment/scope.

## AUTHZ-006

Administrative operations shall be audit logged.

---

# 9. User Requirements

## USER-001

Users shall have a unique system identity.

## USER-002

Users shall belong to an organization where organizational access is applicable.

## USER-003

A user's role shall determine permissions.

## USER-004

Users shall be able to view their own profile.

## USER-005

Users shall not be able to elevate their own privileges.

## USER-006

User deactivation shall prevent future authentication while preserving historical records.

---

# 10. Organization Requirements

The system shall support organizations such as:

- Municipal authorities
- Road agencies
- Maintenance organizations
- Contractors

## ORG-001

An organization shall have a unique identifier.

## ORG-002

Organization membership shall be explicitly associated with users.

## ORG-003

Organization-scoped resources shall not be exposed across unauthorized organizations.

---

# 11. Road Requirements

## ROAD-001

Each road shall have a unique identifier.

## ROAD-002

A road shall have a human-readable name.

## ROAD-003

A road may contain multiple road segments.

## ROAD-004

Road records shall maintain geographic information where available.

## ROAD-005

Road records shall maintain creation and update timestamps.

## ROAD-006

Road deletion should preferably use archival/soft-deletion semantics where historical records depend on the road.

---

# 12. Road Segment Requirements

## SEG-001

Each road segment shall have a unique identifier.

## SEG-002

Each segment shall belong to a road.

## SEG-003

A segment may contain geographic geometry.

## SEG-004

Damage records should reference a segment when sufficient geographic information exists.

## SEG-005

Historical inspection and maintenance relationships shall be retained.

## SEG-006

Segment records shall support future road-health and prediction calculations.

---

# 13. Inspection Requirements

An inspection represents an observation event.

## INS-001

An authorized inspector shall be able to create an inspection.

## INS-002

An inspection shall have a unique identifier.

## INS-003

An inspection shall record its creator.

## INS-004

An inspection shall record creation time.

## INS-005

An inspection may contain road/segment association.

## INS-006

An inspection shall support geographic coordinates.

## INS-007

An inspection shall store GPS accuracy when available.

## INS-008

An inspection shall support one or more media objects.

## INS-009

An inspection shall have a processing status.

## INS-010

An inspection shall preserve failure information when processing fails.

---

# 14. Inspection State Machine

The system shall use controlled inspection states.

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

Failure states may branch from processing stages:

```text
UPLOAD_FAILED
PROCESSING_FAILED
ANALYSIS_FAILED
```

A failed operation shall be retryable where technically possible.

---

# 15. Media Requirements

## MEDIA-001

The system shall support road images.

## MEDIA-002

The system may support video uploads.

## MEDIA-003

Each media object shall have a unique identifier.

## MEDIA-004

Media metadata shall be stored separately from the binary object.

## MEDIA-005

Media shall be associated with an inspection or relevant maintenance workflow.

## MEDIA-006

The server shall validate file type.

## MEDIA-007

The server shall enforce file-size limits.

## MEDIA-008

The server shall not trust client-provided MIME type alone.

## MEDIA-009

Media access shall respect authorization.

## MEDIA-010

Storage URLs/credentials shall not expose unauthorized private media.

---

# 16. AI Processing Requirements

AI processing shall be asynchronous where processing time may be significant.

```text
API
 ↓
Create Processing Job
 ↓
Queue
 ↓
AI Worker
 ↓
Model Inference
 ↓
Persist Results
 ↓
Update Job
```

## AI-001

Every AI processing job shall have a unique identifier.

## AI-002

Every AI result shall record the model name.

## AI-003

Every AI result shall record the model version.

## AI-004

AI processing shall record execution timestamp.

## AI-005

AI failures shall be represented explicitly.

## AI-006

AI processing shall be retryable where appropriate.

## AI-007

The system shall not fabricate detection results when inference fails.

---

# 17. Damage Detection Requirements

## DET-001

The detection engine shall process supported image inputs.

## DET-002

Each detection shall include a damage class.

## DET-003

Each detection shall include confidence.

## DET-004

Object detection results shall include bounding-box coordinates where applicable.

## DET-005

Each detection shall reference its source inspection.

## DET-006

Each detection shall reference the source media/frame.

## DET-007

Detection coordinates shall use a documented coordinate convention.

## DET-008

The configured confidence threshold shall be versioned/configurable.

## DET-009

The system shall retain raw/model-generated values separately from reviewed values.

---

# 18. Damage Classification

Initial supported classes:

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

## CLASS-001

Damage classes shall be represented using stable identifiers.

## CLASS-002

Class names shall not be hard-coded throughout the application.

## CLASS-003

The model class mapping shall be configurable.

## CLASS-004

Adding a new class shall not require redesigning unrelated application modules.

---

# 19. Severity Requirements

Initial levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

## SEV-001

Severity shall be derived from documented measurable factors.

## SEV-002

Severity shall be associated with a detection.

## SEV-003

The system shall retain the severity-generation method/version.

## SEV-004

The system shall preserve relevant input factors where practical.

## SEV-005

Authorized users shall be able to review severity.

## SEV-006

Human corrections shall not silently overwrite the original AI-generated value.

---

# 20. Detection Review

## REV-001

Authorized users shall be able to review a detection.

## REV-002

A reviewer shall be able to confirm a detection.

## REV-003

A reviewer shall be able to reject a false detection.

## REV-004

A reviewer may correct the damage class.

## REV-005

A reviewer may correct severity if authorized.

## REV-006

Review actions shall record reviewer identity and timestamp.

---

# 21. GIS Requirements

## GIS-001

The web application shall provide an interactive map.

## GIS-002

The map shall support road locations.

## GIS-003

The map shall support damage locations.

## GIS-004

The map shall support inspection locations.

## GIS-005

The map shall support maintenance/repair locations where available.

## GIS-006

Map entities shall respect authorization.

## GIS-007

Invalid geographic coordinates shall be rejected.

## GIS-008

The system shall retain coordinate precision appropriate to the source data.

---

# 22. Road Health Requirements

The Road Health Engine shall calculate road-condition indicators from documented inputs.

## HEALTH-001

The calculation shall be deterministic for the same input dataset and model/configuration version.

## HEALTH-002

The system shall store the calculation timestamp.

## HEALTH-003

The system shall store the calculation/model version.

## HEALTH-004

The system shall retain contributing factors.

## HEALTH-005

The system shall distinguish between unavailable data and zero values.

## HEALTH-006

Insufficient data shall produce an explicit "insufficient data" state rather than a fabricated health value.

---

# 23. Maintenance Priority Requirements

## PRIORITY-001

The system shall calculate maintenance priority using documented factors.

## PRIORITY-002

Priority calculation shall be reproducible.

## PRIORITY-003

The system shall store the factors contributing to the result.

## PRIORITY-004

The system shall store the calculation/model version.

## PRIORITY-005

Authorized users shall be able to inspect the factors behind the result.

## PRIORITY-006

Missing inputs shall be handled explicitly.

---

# 24. Prediction Requirements

## PRED-001

Prediction shall only run when the required input data is available.

## PRED-002

The system shall not generate a fabricated prediction when required training/inference inputs are unavailable.

## PRED-003

Each prediction shall record:

- Model name
- Model version
- Feature version/configuration
- Prediction timestamp
- Input-data timestamp
- Prediction horizon

## PRED-004

Prediction outputs shall support uncertainty/confidence information when the selected methodology provides it.

## PRED-005

Predictions shall be presented as estimates rather than guaranteed future events.

---

# 25. Prediction Model Lifecycle

The model lifecycle shall support:

```text
Dataset
   ↓
Training
   ↓
Validation
   ↓
Evaluation
   ↓
Model Artifact
   ↓
Versioning
   ↓
Deployment
   ↓
Inference
   ↓
Monitoring
```

A deployed model shall have a unique version.

---

# 26. Maintenance Requirements

## MAINT-001

Authorized users shall be able to create maintenance jobs.

## MAINT-002

A maintenance job may reference one or more damage records.

## MAINT-003

A maintenance job may reference a road segment.

## MAINT-004

A maintenance job shall have a controlled status.

## MAINT-005

A maintenance job shall support assignment.

## MAINT-006

A maintenance job shall record creation time.

## MAINT-007

A maintenance job shall preserve status history where required.

---

# 27. Maintenance State Machine

The initial state machine shall be:

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

Alternative outcomes:

```text
IN_PROGRESS → CANCELLED

VERIFICATION_PENDING → REJECTED

REJECTED → IN_PROGRESS
```

Invalid transitions shall be rejected by the backend.

---

# 28. Repair Evidence Requirements

## REPAIR-001

Authorized maintenance users shall be able to submit repair evidence.

## REPAIR-002

Evidence shall reference the maintenance job.

## REPAIR-003

Evidence shall record upload time.

## REPAIR-004

Evidence shall record uploader identity.

## REPAIR-005

Evidence may contain:

- Images
- Video
- Notes
- Location
- Completion timestamp

## REPAIR-006

Before and after evidence shall be distinguishable.

---

# 29. Repair Verification Requirements

## VERIFY-001

The system shall support AI-assisted comparison of before/after evidence.

## VERIFY-002

Verification shall produce a structured result.

## VERIFY-003

Verification shall record model/version metadata when AI is used.

## VERIFY-004

Verification shall record timestamp.

## VERIFY-005

Verification shall allow human review.

## VERIFY-006

AI verification shall not automatically remove or alter historical evidence.

---

# 30. Recurrence Requirements

## REC-001

The system shall preserve historical damage records after repair.

## REC-002

New damage observations shall be comparable to historical road locations.

## REC-003

The system shall support geographic association between new and historical damage.

## REC-004

Potential recurrence shall be distinguishable from confirmed recurrence.

## REC-005

Recurrence records shall reference the relevant historical damage/repair chain.

---

# 31. Analytics Requirements

Analytics shall be generated from stored system data.

## ANALYTICS-001

Analytics shall support date filtering.

## ANALYTICS-002

Analytics shall support damage-type filtering.

## ANALYTICS-003

Analytics shall support severity filtering.

## ANALYTICS-004

Analytics shall support road/segment filtering.

## ANALYTICS-005

Analytics shall support maintenance-status filtering.

## ANALYTICS-006

Charts shall clearly identify units and time periods.

## ANALYTICS-007

Empty datasets shall display an explicit empty state.

---

# 32. Reporting Requirements

## REPORT-001

Authorized users shall be able to generate structured reports.

## REPORT-002

Reports shall contain generation timestamp.

## REPORT-003

Reports shall identify the relevant organization/user scope.

## REPORT-004

Reports shall use the filtered dataset represented by the user interface.

## REPORT-005

Generated reports shall not expose unauthorized records.

---

# 33. Android Requirements

## AND-001

The Android application shall authenticate against the backend.

## AND-002

The application shall request location permission when required.

## AND-003

The application shall capture GPS coordinates for inspections where permission is available.

## AND-004

The application shall capture images using Android camera functionality.

## AND-005

The application shall allow the inspector to review captured media before submission.

## AND-006

The application shall upload inspection data securely.

## AND-007

The application shall display upload/processing state.

---

# 34. Android Offline Requirements

## OFF-001

An inspection shall be stored locally before upload when necessary.

## OFF-002

The local queue shall identify upload state.

## OFF-003

The system shall retry failed uploads.

## OFF-004

Successful uploads shall not be uploaded again.

## OFF-005

The user shall be able to identify pending inspections.

## OFF-006

Local queued data shall be protected from unauthorized access as appropriate.

---

# 35. Synchronization Model

The Android synchronization flow shall follow:

```text
LOCAL_DRAFT
     ↓
QUEUED
     ↓
UPLOADING
     ↓
UPLOADED
     ↓
PROCESSING
     ↓
COMPLETED
```

Failure:

```text
QUEUED / UPLOADING
        ↓
UPLOAD_FAILED
        ↓
RETRY
```

Synchronization must use stable identifiers/idempotency mechanisms to prevent duplicate server records.

---

# 36. API Requirements

The backend shall expose versioned REST APIs.

Base structure:

```text
/api/v1/
```

API details will be formally defined in `API_SPECIFICATION.md`.

The API shall:

- Validate input
- Authenticate requests
- Authorize requests
- Return structured responses
- Return consistent errors
- Use appropriate HTTP status codes
- Support pagination for large collections
- Support filtering where required

---

# 37. API Error Contract

Errors should use a consistent structure.

Conceptual format:

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

Internal stack traces must not be returned to clients in production.

---

# 38. Pagination

Large collection endpoints shall support pagination.

The API should avoid returning unrestricted datasets.

Pagination metadata should provide enough information for clients to request additional records.

---

# 39. Filtering and Sorting

Collection endpoints should support documented filtering.

Possible filters:

- Date range
- Status
- Severity
- Damage type
- Road
- Segment
- Organization
- User
- Verification status

Sorting must use documented fields.

---

# 40. Database Requirements

The database shall use PostgreSQL.

## DB-001

Primary records shall have stable unique identifiers.

## DB-002

Foreign-key relationships shall be enforced where appropriate.

## DB-003

Important timestamps shall be stored consistently.

## DB-004

Historical records shall not be silently overwritten.

## DB-005

Database transactions shall be used for operations requiring atomicity.

## DB-006

Indexes shall be added for frequently queried fields.

## DB-007

Geospatial data strategy shall be documented before final schema implementation.

---

# 41. Data Consistency

Operations affecting multiple related entities shall use transactions when necessary.

Example:

```text
Create Maintenance Job
       ↓
Create Job-Damage Relationship
       ↓
Create Audit Entry
```

If the operation requires atomicity, partial success must not be allowed.

---

# 42. Background Processing

Background jobs should be used for operations such as:

- AI inference
- Video frame extraction
- Prediction generation
- Large report generation
- Notification processing
- Retry operations

Conceptual architecture:

```text
FastAPI
   ↓
Create Job
   ↓
Redis Queue
   ↓
Worker
   ↓
Process
   ↓
Database
```

---

# 43. Job Requirements

Every asynchronous job shall have:

- Job ID
- Job type
- Status
- Created timestamp
- Started timestamp where applicable
- Completed timestamp where applicable
- Error information where applicable
- Retry count where applicable

Initial states:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

---

# 44. Idempotency

Operations that may be retried shall be designed to avoid duplicate records.

Particularly important for:

- Android uploads
- Background jobs
- Repair evidence uploads
- AI processing retries
- Notification retries

---

# 45. Logging Requirements

The backend shall generate structured logs.

Logs should include where appropriate:

- Timestamp
- Log level
- Service
- Request ID
- User ID where safe
- Operation
- Error code
- Processing duration

Sensitive values such as passwords and secrets must never be logged.

---

# 46. Request Tracing

The API should assign a request identifier to requests.

The identifier should be usable to correlate:

```text
Client Request
      ↓
FastAPI
      ↓
Database
      ↓
Background Job
      ↓
AI Worker
```

where applicable.

---

# 47. Health Checks

The backend shall expose health-check functionality.

At minimum:

```text
Liveness
Readiness
```

Readiness should verify required dependencies where appropriate.

---

# 48. Configuration Requirements

Application configuration shall be environment-based.

Examples:

```text
DATABASE_URL
JWT_SECRET
STORAGE_ENDPOINT
STORAGE_KEY
REDIS_URL
AI_MODEL_PATH
AI_MODEL_VERSION
API_BASE_URL
```

Actual variable names will be finalized in `DEPLOYMENT.md`.

Secrets shall not be committed to Git.

---

# 49. Frontend Requirements

The web application shall:

- Use TypeScript.
- Use reusable components.
- Use typed API clients.
- Handle loading states.
- Handle errors.
- Handle empty states.
- Protect authenticated routes.
- Respect user permissions.
- Avoid direct database access from the browser.

The browser shall communicate through the backend API.

---

# 50. Frontend State Requirements

The UI shall distinguish:

```text
Loading
Success
Empty
Error
Unauthorized
Processing
```

For AI processing:

```text
Queued
Processing
Completed
Failed
```

---

# 51. Android UI Requirements

The Android application shall:

- Provide clear field workflows.
- Minimize unnecessary interaction while inspecting roads.
- Display GPS state.
- Display network state.
- Display upload state.
- Preserve unsent inspections.
- Clearly indicate synchronization failures.

---

# 52. Security Requirements

## SEC-001

All production API communication shall use HTTPS.

## SEC-002

Secrets shall be stored outside source code.

## SEC-003

Passwords shall use a strong password-hashing algorithm.

## SEC-004

JWT secrets shall be protected.

## SEC-005

API endpoints shall validate authorization.

## SEC-006

Uploaded files shall be validated.

## SEC-007

File access shall be authorization-controlled.

## SEC-008

Rate limiting shall be implemented for sensitive endpoints.

## SEC-009

Database access shall use least-privilege credentials.

## SEC-010

Production error responses shall not expose stack traces.

---

# 53. Input Validation

The backend shall validate:

- Required fields
- Data types
- String lengths
- Enumerations
- Coordinates
- File sizes
- File types
- IDs
- Date/time values
- User permissions

Client-side validation may improve UX but shall never replace server-side validation.

---

# 54. Performance Requirements

The system shall distinguish between:

### Synchronous operations

Examples:

- Authentication
- Simple CRUD
- Small queries
- Status checks

### Asynchronous operations

Examples:

- AI inference
- Video processing
- Large report generation
- Model prediction
- Large media processing

AI processing must not unnecessarily hold an HTTP request open until inference completes.

---

# 55. Reliability Requirements

The system shall:

- Preserve submitted inspection data.
- Retry recoverable background failures.
- Prevent duplicate processing where possible.
- Preserve historical records.
- Handle unavailable dependencies gracefully.
- Provide actionable error states.

---

# 56. Availability Considerations

The system should be designed so that temporary failure of the AI worker does not make the entire platform unusable.

For example:

```text
AI Worker DOWN

Authentication       → Works
Road Management      → Works
Historical Data      → Works
Maintenance Records  → Works
New AI Processing    → Queued
```

When the worker becomes available, queued jobs can resume.

---

# 57. Audit Requirements

Audit logs shall capture important state-changing actions.

Minimum audit fields:

```text
id
actor_id
action
entity_type
entity_id
timestamp
metadata
```

Audit records should be append-oriented and protected from unauthorized modification.

---

# 58. Data Retention

The system should retain historical:

- Inspections
- Detections
- Reviews
- Maintenance records
- Repairs
- Verification results
- Predictions
- Audit records

Deletion policies shall be defined separately based on operational and legal requirements.

---

# 59. Model Versioning

AI results shall never depend only on a generic label such as "YOLO".

Each production result should identify:

```text
Model Family
Model Version
Model Artifact/Identifier
Configuration Version
Inference Timestamp
```

This allows historical results to remain interpretable after model updates.

---

# 60. AI Dataset Separation

Training data shall be separated from production application data.

Recommended structure:

```text
data/
├── raw/
├── processed/
├── annotations/
├── train/
├── validation/
├── test/
└── models/
```

Training datasets must not be mixed with user-uploaded production media without explicit data-management rules.

---

# 61. AI Evaluation Requirements

The detection system shall be evaluated using appropriate metrics including, where applicable:

- Precision
- Recall
- mAP
- Per-class performance
- Inference latency

The prediction system shall use appropriate regression metrics such as:

- MAE
- RMSE
- R²

The exact evaluation methodology will be defined in `AI_ML_SPECIFICATION.md`.

---

# 62. Testing Requirements

The software shall include:

## Unit Tests

For:

- Business logic
- Validation
- Utility functions
- Calculation engines

## Integration Tests

For:

- API + database
- API + storage
- API + queue
- Authentication

## AI Tests

For:

- Model loading
- Inference
- Output schema
- Model-version tracking

## End-to-End Tests

For:

```text
Inspection
 ↓
Upload
 ↓
AI
 ↓
Detection
 ↓
Maintenance
 ↓
Repair
 ↓
Verification
```

---

# 63. Test Environment

Testing should use isolated environments.

Production data must not be used directly for automated tests.

Test configuration should provide:

- Test database
- Test storage
- Test queue
- Mockable AI components where appropriate

---

# 64. Observability Requirements

The system should provide visibility into:

- API health
- Background jobs
- AI processing
- Database connectivity
- Storage failures
- Authentication failures
- Application exceptions

---

# 65. Deployment Requirements

The backend infrastructure shall be containerized.

Initial deployment:

```text
VPS
│
├── Nginx
├── FastAPI
├── AI Worker
└── Redis
```

External managed services:

```text
Supabase PostgreSQL
Supabase Storage
```

Web:

```text
Vercel
```

Android:

```text
APK / Play Store later
```

---

# 66. Environment Requirements

The system shall support:

```text
Development
Staging
Production
```

Each environment shall have separate configuration.

Production secrets must never be copied into source-controlled development configuration.

---

# 67. API and Database Separation

The frontend and Android clients shall never connect directly to privileged PostgreSQL credentials.

The intended path is:

```text
Client
  ↓
FastAPI
  ↓
Database
```

not:

```text
Client
  ↓
PostgreSQL
```

---

# 68. Storage Access Pattern

For private media, the preferred flow is:

```text
Client
  ↓
Request authorized media
  ↓
Backend validates access
  ↓
Signed/authorized storage access
  ↓
Media
```

The system must not expose unrestricted storage credentials to clients.

---

# 69. Error Recovery

Recoverable failures should support retry.

Examples:

```text
Upload Failure
     ↓
Retry

AI Failure
     ↓
Retry Job

Notification Failure
     ↓
Retry

Temporary Database/Storage Failure
     ↓
Retry where safe
```

Non-recoverable failures should be surfaced clearly for human intervention.

---

# 70. Accessibility Requirements

The web application should support:

- Keyboard navigation
- Semantic HTML
- Accessible form labels
- Visible focus states
- Meaningful error messages
- Appropriate contrast
- Non-color-only status indicators

---

# 71. Internationalization Consideration

The initial release may use English as the primary interface language.

The architecture should avoid hard-coding user-facing strings so additional languages can be added later.

---

# 72. Time and Date Handling

The backend shall store timestamps using a consistent timezone-aware representation.

The frontend shall display timestamps according to the user's configured locale/timezone where appropriate.

The system shall not rely on device-local time as the authoritative server timestamp.

---

# 73. Geographic Data Handling

Coordinates shall use a documented geographic reference system.

The default geographic coordinate representation for client/API communication should be documented before implementation.

The system shall validate latitude and longitude ranges.

---

# 74. Privacy Requirements

The platform should collect only data required for its operational purpose.

Location data associated with inspections shall be treated as sensitive operational data.

Access to inspection locations shall respect user authorization.

---

# 75. Demo / Development Mode

If a demonstration environment is implemented, it must be clearly separated from production functionality.

Demo data shall:

- Be clearly identifiable.
- Not be mistaken for real inspections.
- Not pollute production analytics.
- Not bypass production authorization rules.

---

# 76. Seed Data

Development seed data may include:

- Sample roads
- Sample segments
- Sample inspections
- Sample detections
- Sample maintenance jobs

Seed data must be reproducible and version controlled separately from production records.

---

# 77. Feature Flag Requirements

Features that are incomplete or experimental may be controlled using feature flags.

Feature flags must not be used to hide broken production functionality indefinitely.

---

# 78. API Versioning

The initial API version shall be:

```text
/api/v1/
```

Breaking changes should require a new API version or an explicitly managed migration strategy.

---

# 79. Documentation Requirements

Every major module shall document:

- Purpose
- Inputs
- Outputs
- Dependencies
- Error behavior
- Authentication requirements
- Configuration
- Testing requirements

The detailed API contract will be maintained separately in:

`API_SPECIFICATION.md`

---

# 80. Requirement Traceability

Requirements shall maintain traceability across:

```text
PRD
 ↓
SRS
 ↓
Architecture
 ↓
Database
 ↓
API
 ↓
Implementation
 ↓
Tests
```

Example:

```text
PRD FR-004
    ↓
SRS AI-001...AI-007
    ↓
Architecture AI Worker
    ↓
API /ai/jobs
    ↓
Database ai_jobs
    ↓
Implementation
    ↓
Integration Tests
```

---

# 81. Definition of Done

A software requirement is considered implemented only when:

```text
Requirement implemented
        +
Input validation
        +
Authorization
        +
Persistence where required
        +
Error handling
        +
Loading/processing state
        +
Testing
        +
Documentation
```

A UI element without corresponding backend behavior does not satisfy a functional requirement.

---

# 82. Critical System Invariants

The following must always remain true.

### INV-001

A detection must belong to an inspection.

### INV-002

A damage record must preserve its source information.

### INV-003

A maintenance job must preserve its relationship to relevant damage/road records.

### INV-004

A repair must preserve its maintenance relationship.

### INV-005

A verification result must preserve its evidence relationship.

### INV-006

Historical records must not be silently replaced by newer AI results.

### INV-007

AI results must identify their model/version.

### INV-008

Unauthorized users must not access protected resources.

### INV-009

Retryable operations must be designed to avoid unintended duplicates.

### INV-010

Prediction must never be represented as a guaranteed future event.

---

# 83. End-to-End Technical Workflow

The canonical software flow is:

```text
ANDROID
   │
   │ Image + GPS + Metadata
   ▼
FASTAPI
   │
   ├── Validate
   ├── Authenticate
   ├── Authorize
   ├── Create Inspection
   └── Store Media Reference
   │
   ▼
JOB QUEUE
   │
   ▼
AI WORKER
   │
   ├── Load Model
   ├── Infer
   ├── Classify
   ├── Calculate Severity
   └── Persist Results
   │
   ▼
POSTGRESQL
   │
   ├── Detection
   ├── Road Segment
   ├── Road Health
   ├── Prediction
   └── Maintenance
   │
   ▼
WEB DASHBOARD
   │
   ├── Review
   ├── Map
   ├── Analytics
   └── Maintenance
   │
   ▼
REPAIR
   │
   ▼
AFTER-REPAIR EVIDENCE
   │
   ▼
AI VERIFICATION
   │
   ▼
HISTORICAL RECORD
   │
   ▼
RECURRENCE MONITORING
```

---

# 84. SRS Completion Criteria

Before implementation begins, the following technical areas must be sufficiently defined in their respective documents:

```text
[ ] Product requirements        → PRD.md
[ ] Software requirements      → SRS.md
[ ] System architecture        → SYSTEM_ARCHITECTURE.md
[ ] Technology versions        → TECH_STACK.md
[ ] Database schema             → DATABASE_SCHEMA.md
[ ] API contracts               → API_SPECIFICATION.md
[ ] AI/ML architecture          → AI_ML_SPECIFICATION.md
[ ] Role permissions            → USER_ROLES_PERMISSIONS.md
[ ] UI/UX specification         → UI_UX_SPECIFICATION.md
[ ] Android specification       → ANDROID_APP_SPEC.md
[ ] Security specification      → SECURITY.md
[ ] Deployment specification    → DEPLOYMENT.md
[ ] Testing strategy            → TESTING_STRATEGY.md
[ ] Development roadmap         → ROADMAP.md
```

No major implementation decision should be invented during coding when it can be formally defined in the appropriate specification.

---

# 85. Final SRS Principle

The system must maintain a strict separation between:

```text
DATA
 ↓
PROCESSING
 ↓
AI RESULT
 ↓
HUMAN REVIEW
 ↓
BUSINESS ACTION
 ↓
VERIFICATION
 ↓
HISTORICAL RECORD
```

This separation ensures that the platform remains:

- Traceable
- Testable
- Explainable
- Maintainable
- Secure
- Extensible

and prevents the application from becoming a collection of disconnected AI demos.

---

# 86. Final Technical Requirement

The implementation must produce a coherent end-to-end system rather than independent feature screens.

The minimum valid production flow is:

```text
Field Capture
    ↓
Authenticated Upload
    ↓
Validated Storage
    ↓
Asynchronous AI Processing
    ↓
Structured Detection
    ↓
Severity
    ↓
GIS Association
    ↓
Road Intelligence
    ↓
Maintenance Workflow
    ↓
Repair Evidence
    ↓
Verification
    ↓
Historical Record
    ↓
Recurrence Monitoring
```

Every stage must have:

```text
Input
Output
Validation
Authorization
Persistence
Error Handling
Status
Traceability
```

This SRS is the technical behavioral contract for the platform. Architecture, database, API, AI/ML, Android, security, and deployment documents must implement these requirements without contradicting them.