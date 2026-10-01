# API_SPECIFICATION.md

## Road Intelligence & Pothole Management Platform

**Document:** 07 — API Specification  
**Status:** Approved Technical Specification  
**API Style:** REST + JSON  
**Base Version:** `/api/v1/`  
**Backend:** FastAPI + Python  
**Database:** PostgreSQL + PostGIS  
**Authentication:** JWT + RBAC  
**Storage:** Supabase Storage  
**Asynchronous Processing:** Redis + Celery  

---

# 1. Purpose

This document defines the canonical REST API contract for the Road Intelligence & Pothole Management Platform.

It specifies:

- API conventions
- Authentication
- Authorization
- Organization isolation
- Request/response formats
- Error handling
- Pagination
- Filtering
- Sorting
- GIS queries
- File upload workflows
- Inspection APIs
- AI processing APIs
- Damage APIs
- Road health APIs
- Prediction APIs
- Maintenance APIs
- Repair verification APIs
- Recurrence APIs
- Analytics
- Reports
- Notifications
- Audit logs
- Health checks
- Rate limiting
- Idempotency
- Offline synchronization
- API versioning

This document is the implementation contract between:

```text
Web Application
Android Application
        ↓
     REST API
        ↓
Application Services
        ↓
Repositories
        ↓
PostgreSQL / PostGIS / Storage
```

---

# 2. Parent Documents

The API implementation must remain consistent with:

1. `01_PROJECT_CONTEXT.md`
2. `02_PRD.md`
3. `03_SRS.md`
4. `04_SYSTEM_ARCHITECTURE.md`
5. `05_TECH_STACK.md`
6. `06_DATABASE_SCHEMA.md`

If an API requirement conflicts with a higher-level architectural decision, the higher-level source of truth takes precedence.

---

# 3. API Design Principles

The API must follow these principles:

- RESTful resource-oriented design
- JSON-based communication
- HTTPS in all non-local environments
- Explicit authentication and authorization
- Organization-level data isolation
- Server-side validation
- Consistent error responses
- Predictable HTTP status codes
- Idempotent operations where required
- Asynchronous processing for expensive AI operations
- No direct database access from clients
- No secrets exposed to clients
- Large media transferred through object storage
- Historical records must not be silently overwritten
- API contracts must be documented and versioned
- Every important operation must be auditable

---

# 4. Base URLs

The actual domains are environment-specific and must be configured through environment variables.

### Local

```text
http://localhost:<API_PORT>/api/v1
```

### Staging

```text
https://<STAGING_API_DOMAIN>/api/v1
```

### Production

```text
https://<PRODUCTION_API_DOMAIN>/api/v1
```

The application must never hard-code environment-specific API domains.

---

# 5. API Versioning

The initial API version is:

```text
/api/v1/
```

Example:

```text
GET /api/v1/roads
```

Breaking API changes require a new version.

Example:

```text
/api/v2/
```

Non-breaking additions may remain within the existing version.

Examples of generally non-breaking changes:

- Adding optional response fields
- Adding optional request fields
- Adding new endpoints
- Adding new filter options

Breaking changes include:

- Removing fields
- Changing field meaning
- Changing required fields
- Changing response structure
- Changing authentication behavior

---

# 6. Transport and Content Types

## 6.1 Request

JSON requests must use:

```http
Content-Type: application/json
```

unless the endpoint explicitly requires another content type.

File uploads are performed through Supabase Storage signed URLs rather than sending large binary files through normal API requests.

## 6.2 Response

Normal API responses use:

```http
Content-Type: application/json
```

---

# 7. Authentication

Authentication uses JWT.

The client sends:

```http
Authorization: Bearer <access_token>
```

Access tokens represent the authenticated user.

The backend must validate:

- Token signature
- Token expiration
- User identity
- Organization membership
- Account status
- Required permissions

---

# 8. Refresh Tokens

If refresh tokens are enabled, the flow is:

```text
Login
 ↓
Access Token + Refresh Token
 ↓
Access Token expires
 ↓
Refresh Token
 ↓
New Access Token
```

Refresh tokens must be stored securely and must not be exposed in URLs.

The database may persist refresh-token metadata according to `DATABASE_SCHEMA.md`.

---

# 9. Authentication Endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/login` | Public | Authenticate user |
| POST | `/auth/refresh` | Refresh token | Refresh access token |
| POST | `/auth/logout` | Required | Invalidate session/token |
| GET | `/auth/me` | Required | Get authenticated user |
| POST | `/auth/change-password` | Required | Change password |

---

# 10. Login

### Request

```http
POST /api/v1/auth/login
```

```json
{
  "email": "inspector@example.com",
  "password": "password"
}
```

### Response

```json
{
  "data": {
    "access_token": "<JWT>",
    "refresh_token": "<REFRESH_TOKEN>",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "meta": {}
}
```

Invalid credentials must return a generic authentication error rather than revealing whether an email exists.

---

# 11. Current User

```http
GET /api/v1/auth/me
```

Example response:

```json
{
  "data": {
    "id": "uuid",
    "email": "inspector@example.com",
    "name": "Field Inspector",
    "status": "ACTIVE",
    "organizations": [
      {
        "organization_id": "uuid",
        "role": "INSPECTOR"
      }
    ]
  },
  "meta": {}
}
```

---

# 12. Organization Context

Every authenticated request operates within an organization context.

The API must ensure that a user can only access resources belonging to organizations in which they have valid membership.

Organization selection may be supplied through:

```http
X-Organization-ID: <organization_uuid>
```

The backend must validate that the authenticated user belongs to that organization.

The server must never trust an organization ID supplied by a client without authorization validation.

---

# 13. Roles

The initial roles are:

```text
ADMINISTRATOR
ROAD_AUTHORITY
FIELD_INSPECTOR
CONTRACTOR
```

Permissions are checked server-side.

Example permission categories:

```text
road:read
road:create
road:update

inspection:create
inspection:read
inspection:submit

damage:read
damage:review
damage:update

maintenance:create
maintenance:assign
maintenance:update

repair:submit
repair:verify

analytics:read
reports:create

audit:read
user:manage
```

---

# 14. Request ID

Every request should receive a unique request ID.

Client may provide:

```http
X-Request-ID: <uuid>
```

If absent, the API generates one.

The request ID must appear in:

- Logs
- Error responses
- Background-job metadata where applicable
- Audit context where applicable

---

# 15. Standard Success Response

Single-resource response:

```json
{
  "data": {
    "id": "uuid",
    "name": "Example"
  },
  "meta": {}
}
```

---

# 16. Standard List Response

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

Pagination parameters:

```text
page
page_size
```

Default:

```text
page = 1
page_size = 20
```

Maximum:

```text
page_size = 100
```

High-volume endpoints may later introduce cursor pagination without changing the underlying resource model.

---

# 17. Standard Error Response

All API errors must follow the SRS error contract:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found.",
    "details": {},
    "request_id": "uuid"
  }
}
```

The API must not expose:

- Stack traces
- Database credentials
- SQL queries
- Internal file paths
- Secret keys
- Internal infrastructure details

---

# 18. Error Codes

Initial standardized error codes include:

```text
AUTHENTICATION_REQUIRED
INVALID_CREDENTIALS
TOKEN_EXPIRED
TOKEN_INVALID
FORBIDDEN
ORGANIZATION_ACCESS_DENIED

VALIDATION_ERROR
INVALID_STATE_TRANSITION
RESOURCE_NOT_FOUND
RESOURCE_CONFLICT
DUPLICATE_RESOURCE

IDEMPOTENCY_CONFLICT
UPLOAD_NOT_FOUND
UPLOAD_EXPIRED

PROCESSING_FAILED
JOB_NOT_FOUND
JOB_ALREADY_RUNNING

AI_ANALYSIS_FAILED
MODEL_NOT_AVAILABLE

INSUFFICIENT_DATA
PREDICTION_UNAVAILABLE

RATE_LIMIT_EXCEEDED
REQUEST_TOO_LARGE

INTERNAL_SERVER_ERROR
SERVICE_UNAVAILABLE
```

---

# 19. HTTP Status Codes

| Status | Usage |
|---|---|
| 200 | Successful read/update |
| 201 | Resource created |
| 202 | Async operation accepted |
| 204 | Successful operation without response body |
| 400 | Invalid request |
| 401 | Authentication required/invalid |
| 403 | Permission denied |
| 404 | Resource not found |
| 409 | Resource/state conflict |
| 413 | Request too large |
| 422 | Validation failure |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service unavailable |

---

# 20. Validation

All incoming requests must be validated using Pydantic schemas.

Validation must occur before:

```text
Business logic
Database mutation
AI processing
Storage operation
```

Validation includes:

- Required fields
- Data types
- UUID format
- Enum values
- Numeric ranges
- Geographic coordinates
- Timestamp validity
- File metadata
- Organization access
- State transitions

---

# 21. Filtering

List endpoints support query parameters.

Example:

```http
GET /api/v1/damages?
severity=HIGH&
status=CONFIRMED&
damage_type=POTHOLE
```

Multiple values may be supported using comma-separated values:

```text
severity=HIGH,CRITICAL
```

---

# 22. Sorting

Example:

```text
?sort=-created_at
```

Ascending:

```text
?sort=created_at
```

Descending:

```text
?sort=-created_at
```

Only explicitly supported fields may be sortable.

Clients must not supply arbitrary SQL expressions.

---

# 23. Search

Text-searchable endpoints may support:

```text
?search=MG Road
```

Search implementation must use parameterized queries.

---

# 24. Date Filtering

Standard parameters:

```text
from
to
```

Example:

```http
GET /api/v1/inspections?from=2026-09-01T00:00:00Z&to=2026-09-30T23:59:59Z
```

All timestamps must be interpreted as UTC unless explicitly documented otherwise.

---

# 25. Geographic Filtering

GIS endpoints support bounding-box filtering.

Example:

```text
?min_lat=18.500
&min_lon=73.800
&max_lat=18.600
&max_lon=73.950
```

The backend must validate coordinate ranges.

Latitude:

```text
-90 to 90
```

Longitude:

```text
-180 to 180
```

PostGIS must perform authoritative spatial queries.

---

# 26. Idempotency

Operations that can be retried by mobile clients must support:

```http
Idempotency-Key: <unique-key>
```

This is particularly important for:

- Inspection creation
- Media completion
- Processing requests
- Maintenance creation
- Repair evidence submission
- Report generation

Repeated requests using the same valid key must not create duplicate resources.

---

# 27. Authentication Endpoint Matrix

| Method | Endpoint | Role |
|---|---|---|
| POST | `/auth/login` | Public |
| POST | `/auth/refresh` | Refresh token |
| POST | `/auth/logout` | Authenticated |
| GET | `/auth/me` | Authenticated |
| POST | `/auth/change-password` | Authenticated |

---

# 28. User and Organization APIs

## 28.1 List Organizations

```http
GET /organizations
```

## 28.2 Get Organization

```http
GET /organizations/{organization_id}
```

## 28.3 List Members

```http
GET /organizations/{organization_id}/members
```

## 28.4 Add Member

```http
POST /organizations/{organization_id}/members
```

Example:

```json
{
  "email": "inspector@example.com",
  "role": "FIELD_INSPECTOR"
}
```

## 28.5 Update Membership

```http
PATCH /organizations/{organization_id}/members/{membership_id}
```

Only authorized administrators may manage organization memberships.

---

# 29. Road APIs

## 29.1 List Roads

```http
GET /roads
```

Supported filters may include:

```text
search
status
road_type
district
city
page
page_size
sort
```

## 29.2 Create Road

```http
POST /roads
```

Example:

```json
{
  "name": "Example Road",
  "road_code": "RD-001",
  "road_type": "URBAN",
  "geometry": {
    "type": "LineString",
    "coordinates": [
      [73.8567, 18.5204],
      [73.8600, 18.5230]
    ]
  }
}
```

## 29.3 Get Road

```http
GET /roads/{road_id}
```

## 29.4 Update Road

```http
PATCH /roads/{road_id}
```

## 29.5 List Road Segments

```http
GET /roads/{road_id}/segments
```

## 29.6 Create Road Segment

```http
POST /roads/{road_id}/segments
```

## 29.7 Get Segment

```http
GET /road-segments/{segment_id}
```

## 29.8 Update Segment

```http
PATCH /road-segments/{segment_id}
```

---

# 30. Inspection APIs

## 30.1 Create Inspection

```http
POST /inspections
```

Example:

```json
{
  "client_id": "uuid",
  "road_id": "uuid",
  "road_segment_id": "uuid",
  "inspection_type": "FIELD",
  "captured_at": "2026-10-01T08:30:00Z",
  "location": {
    "latitude": 18.5204,
    "longitude": 73.8567,
    "accuracy_m": 5.2
  }
}
```

The `client_id` allows an Android device to preserve identity during offline synchronization.

---

# 31. Get Inspections

```http
GET /inspections
```

Supported filters:

```text
status
inspector_id
road_id
road_segment_id
inspection_type
from
to
page
page_size
sort
```

---

# 32. Get Inspection

```http
GET /inspections/{inspection_id}
```

The response should include:

- Inspection metadata
- Current state
- Road
- Road segment
- Inspector
- Location
- Media summary
- Processing status
- AI processing summary
- Review status

---

# 33. Update Inspection

```http
PATCH /inspections/{inspection_id}
```

Only mutable fields may be updated.

Historical analytical results must not be silently replaced.

---

# 34. Submit Inspection

```http
POST /inspections/{inspection_id}/submit
```

Expected state transition:

```text
DRAFT → SUBMITTED
```

Invalid transitions return:

```text
409 INVALID_STATE_TRANSITION
```

---

# 35. Inspection Media Upload

Large files must use the signed-upload workflow.

## Step 1 — Request Upload URL

```http
POST /inspections/{inspection_id}/media/upload-url
```

Example:

```json
{
  "filename": "inspection_001.mp4",
  "content_type": "video/mp4",
  "size_bytes": 52428800,
  "checksum": "<optional-checksum>"
}
```

Response:

```json
{
  "data": {
    "upload_url": "<SIGNED_URL>",
    "storage_path": "<PATH>",
    "expires_in": 900
  },
  "meta": {}
}
```

## Step 2 — Client Uploads

The client uploads directly to Supabase Storage using the signed URL.

## Step 3 — Complete Upload

```http
POST /inspections/{inspection_id}/media/complete
```

Example:

```json
{
  "storage_path": "<PATH>",
  "media_type": "VIDEO",
  "size_bytes": 52428800,
  "checksum": "<checksum>"
}
```

The backend validates the upload and creates the media metadata record.

---

# 36. List Inspection Media

```http
GET /inspections/{inspection_id}/media
```

Media responses contain metadata and authorized access information rather than permanent service credentials.

---

# 37. Start Inspection Processing

```http
POST /inspections/{inspection_id}/process
```

Response:

```http
202 Accepted
```

```json
{
  "data": {
    "job_id": "uuid",
    "status": "QUEUED"
  },
  "meta": {}
}
```

The endpoint must not perform long-running AI inference synchronously.

---

# 38. Processing Job APIs

## Get Job

```http
GET /jobs/{job_id}
```

Example:

```json
{
  "data": {
    "id": "uuid",
    "job_type": "AI_ANALYSIS",
    "status": "RUNNING",
    "progress": 0.65,
    "created_at": "2026-10-01T08:40:00Z",
    "started_at": "2026-10-01T08:41:00Z"
  },
  "meta": {}
}
```

Supported states:

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

---

# 39. AI Detection APIs

## Get Inspection Detections

```http
GET /inspections/{inspection_id}/detections
```

The response may contain:

```json
{
  "data": [
    {
      "id": "uuid",
      "damage_type": "POTHOLE",
      "confidence": 0.94,
      "severity": "HIGH",
      "location": {
        "latitude": 18.5204,
        "longitude": 73.8567
      },
      "bbox": {
        "x_min": 0.12,
        "y_min": 0.25,
        "x_max": 0.42,
        "y_max": 0.67
      },
      "model_version": "yolo-road-v1.0.0"
    }
  ],
  "meta": {}
}
```

Raw AI detections and canonical damage records must remain conceptually separate.

---

# 40. Damage Type API

```http
GET /damage-types
```

Initial types:

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

---

# 41. Damage APIs

## List Damages

```http
GET /damages
```

Filters:

```text
damage_type
severity
status
road_id
road_segment_id
inspection_id
from
to
page
page_size
sort
```

## Get Damage

```http
GET /damages/{damage_id}
```

## Update Damage

```http
PATCH /damages/{damage_id}
```

Updates must preserve the original AI detection and audit history.

---

# 42. Damage Review

```http
POST /damages/{damage_id}/review
```

Example:

```json
{
  "decision": "CONFIRMED",
  "severity": "HIGH",
  "notes": "Confirmed during field review."
}
```

Possible decisions:

```text
CONFIRMED
REJECTED
```

A human reviewer must be recorded.

---

# 43. GIS Map APIs

## Map Damages

```http
GET /map/damages
```

Example:

```text
GET /map/damages?
min_lat=18.50&
min_lon=73.80&
max_lat=18.60&
max_lon=73.95&
severity=HIGH,CRITICAL
```

Response should be optimized for map rendering.

---

# 44. Map Roads

```http
GET /map/roads
```

Returns road geometries and relevant summary properties.

---

# 45. Map Segments

```http
GET /map/segments
```

May return:

- Segment geometry
- Road health
- Damage count
- Severity summary
- Maintenance status
- Priority score

---

# 46. Road Health APIs

## Road Health

```http
GET /roads/{road_id}/health
```

## Segment Health

```http
GET /road-segments/{segment_id}/health
```

Example:

```json
{
  "data": {
    "road_segment_id": "uuid",
    "health_score": 68.4,
    "calculated_at": "2026-10-01T09:00:00Z",
    "model_version": "health-v1",
    "factors": {
      "damage_density": 0.22,
      "severity": 0.18,
      "recurrence": 0.11,
      "inspection_freshness": 0.08
    }
  },
  "meta": {}
}
```

The exact health formula is governed by the approved road-health specification and must not be invented independently by API developers.

---

# 47. Deterioration Prediction APIs

## Get Predictions

```http
GET /road-segments/{segment_id}/predictions
```

## Request Prediction

```http
POST /road-segments/{segment_id}/predictions
```

Response:

```http
202 Accepted
```

```json
{
  "data": {
    "job_id": "uuid",
    "status": "QUEUED"
  },
  "meta": {}
}
```

Predictions must include:

- Segment
- Prediction timestamp
- Forecast horizon
- Predicted condition/risk
- Model version
- Feature version where available
- Confidence/uncertainty where supported
- Input data timestamp

Predictions are estimates and must never be represented as guaranteed outcomes.

---

# 48. Maintenance APIs

## List Maintenance Jobs

```http
GET /maintenance-jobs
```

Filters:

```text
status
priority
road_id
road_segment_id
assigned_to
contractor
from
to
page
page_size
sort
```

## Create Maintenance Job

```http
POST /maintenance-jobs
```

Example:

```json
{
  "road_id": "uuid",
  "road_segment_id": "uuid",
  "priority": "HIGH",
  "title": "Repair severe pothole cluster",
  "description": "Repair confirmed damage on segment.",
  "target_date": "2026-10-10"
}
```

---

# 49. Get Maintenance Job

```http
GET /maintenance-jobs/{maintenance_job_id}
```

The response should include:

- Job details
- Linked damage
- Road/segment
- Assignment
- Current status
- Status history
- Repair evidence
- Verification status

---

# 50. Update Maintenance Job

```http
PATCH /maintenance-jobs/{maintenance_job_id}
```

Only authorized fields may be modified.

---

# 51. Assign Maintenance Job

```http
POST /maintenance-jobs/{maintenance_job_id}/assign
```

Example:

```json
{
  "assigned_to": "uuid"
}
```

---

# 52. Maintenance Status Transition

```http
POST /maintenance-jobs/{maintenance_job_id}/status
```

Example:

```json
{
  "status": "IN_PROGRESS",
  "notes": "Repair crew started work."
}
```

Valid lifecycle:

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

The API must reject invalid state transitions.

---

# 53. Maintenance History

```http
GET /maintenance-jobs/{maintenance_job_id}/history
```

Returns chronological status transitions.

Each history record should contain:

```text
previous_status
new_status
changed_by
changed_at
notes
```

---

# 54. Maintenance Damage Links

Damage relationships must be preserved.

The API may expose linked damage through:

```http
GET /maintenance-jobs/{maintenance_job_id}/damages
```

A maintenance job may be associated with multiple damage records.

---

# 55. Repair Evidence Upload

## Request Signed URL

```http
POST /maintenance-jobs/{maintenance_job_id}/repair-evidence/upload-url
```

Example:

```json
{
  "filename": "repair_after.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 5242880
}
```

## Complete Upload

```http
POST /maintenance-jobs/{maintenance_job_id}/repair-evidence/complete
```

Example:

```json
{
  "storage_path": "<PATH>",
  "captured_at": "2026-10-05T10:30:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567
}
```

---

# 56. Repair Evidence List

```http
GET /maintenance-jobs/{maintenance_job_id}/repair-evidence
```

Returns metadata and authorized access information.

---

# 57. Repair Verification

## Submit Verification

```http
POST /maintenance-jobs/{maintenance_job_id}/verify
```

Example:

```json
{
  "decision": "VERIFIED",
  "notes": "Repair evidence confirms restoration."
}
```

Possible outcomes:

```text
VERIFIED
REJECTED
```

Verification may use:

- AI analysis
- Human review
- Evidence metadata
- Before/after comparison
- Damage recurrence indicators

The verification result must preserve the AI model/version when AI is involved.

---

# 58. Recurrence APIs

## List Recurrence Records

```http
GET /recurrence
```

Filters:

```text
road_id
road_segment_id
damage_type
severity
status
from
to
```

## Get Recurrence Record

```http
GET /recurrence/{recurrence_id}
```

## Review Recurrence

```http
POST /recurrence/{recurrence_id}/review
```

Example:

```json
{
  "status": "CONFIRMED",
  "notes": "Same location shows repeated damage."
}
```

Recurrence analysis must preserve historical relationships between:

```text
Original Damage
→ Maintenance
→ Repair
→ Verification
→ New Damage
→ Recurrence
```

---

# 59. Dashboard API

```http
GET /dashboard/summary
```

Possible metrics:

```text
total_roads
total_segments
active_inspections
open_damages
high_severity_damages
critical_damages
maintenance_open
maintenance_in_progress
verification_pending
verified_repairs
recurrence_count
average_road_health
```

Dashboard calculations must use authorized organization-scoped data.

---

# 60. Damage Analytics

```http
GET /analytics/damage-trends
```

Supported filters:

```text
from
to
road_id
damage_type
severity
```

Possible response:

```json
{
  "data": {
    "series": [
      {
        "date": "2026-10-01",
        "count": 23
      }
    ]
  },
  "meta": {}
}
```

---

# 61. Road Health Analytics

```http
GET /analytics/road-health
```

May return:

- Average health
- Health distribution
- Segment-level health
- Historical changes
- Critical segments

---

# 62. Maintenance Analytics

```http
GET /analytics/maintenance
```

May include:

- Open jobs
- Completed jobs
- Verification rate
- Average completion time
- Rejected repairs
- Recurrence after repair

---

# 63. Reports

## Generate Report

```http
POST /reports
```

Example:

```json
{
  "report_type": "ROAD_HEALTH",
  "road_id": "uuid",
  "from": "2026-09-01T00:00:00Z",
  "to": "2026-09-30T23:59:59Z",
  "format": "PDF"
}
```

Report generation may be asynchronous.

Response:

```http
202 Accepted
```

```json
{
  "data": {
    "report_id": "uuid",
    "status": "QUEUED"
  },
  "meta": {}
}
```

---

# 64. Report APIs

```http
GET /reports
```

```http
GET /reports/{report_id}
```

```http
GET /reports/{report_id}/download-url
```

Download URLs must be short-lived signed URLs.

---

# 65. Notifications

## List Notifications

```http
GET /notifications
```

## Mark Notification Read

```http
POST /notifications/{notification_id}/read
```

## Mark All Read

```http
POST /notifications/read-all
```

---

# 66. Audit Logs

Audit logs are restricted to authorized administrative roles.

```http
GET /audit-logs
```

Supported filters:

```text
user_id
action
resource_type
resource_id
from
to
page
page_size
```

Audit records should include:

```text
actor
organization
action
resource
timestamp
request_id
metadata
```

Sensitive values must not be logged.

---

# 67. Health Endpoints

## Liveness

```http
GET /health/live
```

Response:

```json
{
  "status": "ok"
}
```

Liveness confirms that the API process is running.

---

# 68. Readiness

```http
GET /health/ready
```

Readiness checks required dependencies such as:

- PostgreSQL
- Redis
- Required storage connectivity
- Required configuration

Example:

```json
{
  "status": "ready",
  "dependencies": {
    "database": "ok",
    "redis": "ok",
    "storage": "ok"
  }
}
```

---

# 69. Metrics

A metrics endpoint may be exposed internally:

```text
/metrics
```

It must not be publicly accessible without appropriate protection.

Metrics may include:

- Request count
- Request latency
- Error rate
- Job processing time
- Queue depth
- AI inference time
- Database latency

---

# 70. Android Offline Synchronization

The Android application must support operation when network connectivity is unavailable.

Local records receive UUIDs before synchronization.

Example:

```text
Android
 ↓
Create local inspection UUID
 ↓
Room
 ↓
Offline Queue
 ↓
Network Available
 ↓
POST /inspections
 ↓
Upload media
 ↓
Submit inspection
 ↓
Start processing
```

---

# 71. Offline Inspection Creation

The Android client sends:

```http
POST /inspections
Idempotency-Key: <client-generated-key>
```

The same request may safely be retried.

The backend must return the same logical resource rather than creating duplicates.

---

# 72. Sync Conflict Handling

Possible conflicts include:

```text
RESOURCE_CONFLICT
INVALID_STATE_TRANSITION
DUPLICATE_RESOURCE
UPLOAD_NOT_FOUND
```

The API must return enough information for the Android synchronization layer to decide whether to:

- Retry
- Refresh
- Mark as failed
- Ask for user intervention

The backend must not silently overwrite newer server state.

---

# 73. AI Processing Architecture

The API must never perform long-running AI inference inside the request-response cycle.

Correct flow:

```text
POST /inspections/{id}/process
          ↓
Validate
          ↓
Create processing job
          ↓
Queue Redis/Celery
          ↓
Return 202
          ↓
AI Worker
          ↓
YOLO/OpenCV
          ↓
Classification
          ↓
Severity
          ↓
Persist results
```

---

# 74. AI Model Metadata

Every AI result must identify:

```text
model_id
model_version
processing_run_id
processed_at
```

Where applicable:

```text
dataset_version
preprocessing_version
feature_version
```

AI results without traceable model metadata are invalid for production workflows.

---

# 75. AI Failure Handling

If AI processing fails:

```text
processing_job.status = FAILED
```

The API should expose:

```json
{
  "error": {
    "code": "AI_ANALYSIS_FAILED",
    "message": "AI analysis could not be completed.",
    "details": {
      "job_id": "uuid"
    },
    "request_id": "uuid"
  }
}
```

Internal technical details belong in server logs, not public error messages.

---

# 76. File Upload Security

The API must enforce:

- Allowed MIME types
- Maximum file size
- Organization-scoped storage paths
- Signed URLs
- Short URL expiration
- File metadata validation
- Optional checksum verification
- No client access to storage service-role credentials

Clients must never receive:

```text
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL
JWT signing secret
SMTP credentials
AI model credentials
Redis credentials
```

---

# 77. Rate Limiting

Rate limits should be applied especially to:

```text
/auth/login
/auth/refresh
/upload-url endpoints
/report generation
AI processing requests
```

The exact production values should be environment-configurable.

A rate-limit response returns:

```http
429 Too Many Requests
```

---

# 78. Request Size Limits

The API must reject excessively large JSON requests.

Large media files must use signed object-storage uploads.

The backend should define environment-specific limits for:

```text
JSON body
metadata payload
report request
batch operations
```

---

# 79. CORS

CORS must explicitly allow only configured application origins.

Development may use local origins.

Production must use the configured production web domain.

Wildcard origins must not be used in production when credentials are involved.

---

# 80. API Security Requirements

The API must:

- Validate every authenticated request
- Enforce RBAC
- Enforce organization isolation
- Use parameterized queries
- Validate UUIDs
- Validate geographic data
- Validate state transitions
- Protect signed URLs
- Avoid information leakage
- Avoid insecure direct object references
- Log security-relevant events
- Apply rate limits
- Use HTTPS
- Never expose secrets

---

# 81. Resource Authorization

Resource ownership must be checked before returning or modifying data.

Example:

```text
GET /damages/{damage_id}
```

must verify:

```text
Authenticated User
        ↓
Organization Membership
        ↓
Damage Organization
        ↓
Permission
        ↓
Resource Access
```

Knowing a UUID must never be sufficient to access a resource.

---

# 82. API State Transition Rules

The API is responsible for enforcing state machines.

### Inspection

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

### Maintenance

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

Alternative:

```text
IN_PROGRESS → CANCELLED
VERIFICATION_PENDING → REJECTED
REJECTED → IN_PROGRESS
```

Invalid transitions return:

```text
409 INVALID_STATE_TRANSITION
```

---

# 83. API Resource Naming

Use plural nouns for collections:

```text
/roads
/inspections
/damages
/maintenance-jobs
/notifications
/reports
```

Use resource IDs:

```text
/roads/{id}
/inspections/{id}
/damages/{id}
```

Avoid action-heavy URLs except for explicit state-changing operations:

```text
/submit
/review
/verify
/assign
/process
```

---

# 84. API DTO Layers

The backend must distinguish:

```text
Database Models
        ↓
Domain Models
        ↓
Request DTOs
        ↓
Response DTOs
```

SQLAlchemy models must not automatically become public API contracts.

This prevents accidental exposure of internal fields.

---

# 85. Important API DTOs

The implementation should define dedicated Pydantic schemas for:

```text
UserResponse
OrganizationResponse
RoadCreate
RoadUpdate
RoadResponse
RoadSegmentCreate
RoadSegmentUpdate
RoadSegmentResponse
InspectionCreate
InspectionUpdate
InspectionResponse
MediaUploadRequest
MediaCompleteRequest
ProcessingJobResponse
DetectionResponse
DamageResponse
DamageReviewRequest
RoadHealthResponse
PredictionResponse
MaintenanceJobCreate
MaintenanceJobUpdate
MaintenanceJobResponse
MaintenanceStatusRequest
RepairEvidenceRequest
RepairVerificationRequest
RecurrenceResponse
ReportCreate
ReportResponse
NotificationResponse
AuditLogResponse
```

---

# 86. API Response Stability

Response fields should be explicitly documented.

The API must avoid returning raw database objects.

Sensitive/internal fields must remain private.

Examples of fields that should not normally be returned:

```text
password_hash
refresh_token_hash
internal storage credentials
database metadata
internal exception details
```

---

# 87. Batch Operations

Batch endpoints should only be introduced when there is a clear performance requirement.

For example:

```text
POST /inspections/batch-sync
```

may be introduced later for mobile synchronization.

Batch operations must still enforce:

- Per-record validation
- Organization isolation
- Authorization
- Idempotency
- Partial failure reporting

---

# 88. API Documentation

FastAPI should generate OpenAPI documentation.

Development may expose:

```text
/docs
/redoc
/openapi.json
```

Production documentation should be:

- Disabled, or
- Protected by authentication/network restrictions.

The OpenAPI contract must be generated from the actual implementation and kept aligned with this document.

---

# 89. API Logging

Each request should record structured metadata such as:

```text
request_id
timestamp
method
path
status_code
duration_ms
user_id
organization_id
```

Do not log:

```text
passwords
JWT tokens
refresh tokens
service-role keys
API keys
signed URLs where avoidable
sensitive personal information
```

---

# 90. API Observability

The API should expose operational metrics for:

```text
request latency
request volume
5xx rate
4xx rate
database latency
Redis latency
AI job queue depth
AI processing duration
failed jobs
storage failures
```

Logs must be correlated through request IDs and job IDs.

---

# 91. API Performance Requirements

Target behavior:

- Simple authenticated API requests should normally complete within hundreds of milliseconds.
- Large media must never block API requests.
- AI inference must be asynchronous.
- Dashboard queries should use optimized aggregate queries.
- GIS queries must use PostGIS spatial indexes.
- List endpoints must paginate.
- N+1 database queries must be avoided.
- Expensive analytics should use optimized queries or precomputed snapshots where appropriate.

---

# 92. API Reliability

The API must tolerate:

- Mobile network interruptions
- Duplicate requests
- AI worker failures
- Redis interruptions
- Temporary storage failures
- Database transient failures

Retryable operations must be designed for idempotency.

Non-retryable errors must be explicitly classified.

---

# 93. Transaction Requirements

Database mutations involving multiple related records must use transactions.

Examples:

```text
Maintenance creation
+ damage links
+ audit record
```

```text
Repair verification
+ maintenance status transition
+ audit record
```

must either complete consistently or roll back.

---

# 94. Background Job Integration

API requests create jobs through Redis/Celery where required.

Example:

```text
API
 ↓
processing_jobs
 ↓
Redis
 ↓
Celery
 ↓
AI Worker
 ↓
processing_jobs update
 ↓
database results
```

Job creation must be idempotent.

---

# 95. API and Storage Separation

The API controls:

```text
authorization
metadata
storage paths
signed URL generation
upload completion
validation
```

Supabase Storage handles:

```text
large media
repair evidence
reports
model artifacts
```

PostgreSQL stores metadata and relationships, not large binary files.

---

# 96. API and AI Separation

The FastAPI service is responsible for:

```text
authentication
authorization
validation
job creation
result retrieval
workflow orchestration
```

The AI worker is responsible for:

```text
model loading
preprocessing
inference
postprocessing
severity analysis
prediction
verification analysis
AI result persistence
```

The web or Android client must never directly execute the production AI model.

---

# 97. Example Complete Inspection Flow

```text
1. Android authenticates
        ↓
2. POST /inspections
        ↓
3. Backend creates inspection
        ↓
4. POST /inspections/{id}/media/upload-url
        ↓
5. Android uploads media to Storage
        ↓
6. POST /inspections/{id}/media/complete
        ↓
7. POST /inspections/{id}/submit
        ↓
8. POST /inspections/{id}/process
        ↓
9. API returns job ID
        ↓
10. AI Worker processes media
        ↓
11. AI detections persisted
        ↓
12. Damage records created
        ↓
13. Inspector reviews results
        ↓
14. Damage confirmed
        ↓
15. Maintenance job created
```

---

# 98. Example Repair Flow

```text
Maintenance Job
      ↓
IN_PROGRESS
      ↓
Repair completed
      ↓
Repair evidence upload
      ↓
VERIFICATION_PENDING
      ↓
AI/Human verification
      ↓
VERIFIED
      ↓
Historical record
      ↓
Future inspections
      ↓
Recurrence detection
```

---

# 99. API Contract Rules for Coding Agents

Any coding agent implementing this API must:

1. Read all approved project documents first.
2. Never invent new architecture without approval.
3. Never bypass FastAPI authentication.
4. Never bypass organization authorization.
5. Never expose database credentials.
6. Never expose Supabase service-role credentials.
7. Never expose AI secrets.
8. Never allow direct client database access.
9. Never perform long-running AI inference synchronously.
10. Preserve existing API contracts.
11. Use Pydantic request/response schemas.
12. Use SQLAlchemy repositories/services.
13. Use Alembic for schema changes.
14. Validate all state transitions.
15. Implement idempotency where specified.
16. Preserve historical records.
17. Record audit events for important mutations.
18. Return the standard error envelope.
19. Write tests for new endpoints.
20. Update OpenAPI documentation when contracts change.
21. Never return fake AI results.
22. Never silently swallow failures.
23. Never hard-code secrets.
24. Never replace production PostgreSQL with SQLite.
25. Never introduce external generative AI APIs into the architecture.

---

# 100. API Testing Requirements

Every endpoint must have tests covering, where applicable:

### Authentication

```text
valid credentials
invalid credentials
expired token
missing token
```

### Authorization

```text
authorized role
unauthorized role
wrong organization
resource not owned by organization
```

### Validation

```text
missing fields
invalid UUID
invalid enum
invalid coordinates
invalid timestamps
invalid state
```

### Business Logic

```text
valid state transition
invalid state transition
duplicate operation
historical record preservation
```

### Reliability

```text
retry
idempotency
worker failure
storage failure
```

---

# 101. API Definition of Done

An API feature is complete only when:

```text
Requirement defined
        ↓
Endpoint designed
        ↓
Request schema created
        ↓
Response schema created
        ↓
Authentication implemented
        ↓
Authorization implemented
        ↓
Validation implemented
        ↓
Business logic implemented
        ↓
Database interaction implemented
        ↓
Error handling implemented
        ↓
Audit requirements implemented
        ↓
Tests implemented
        ↓
OpenAPI documented
        ↓
Frontend/Android integration verified
```

---

# 102. Canonical API Architecture

The final API architecture is:

```text
                WEB
                 │
              ANDROID
                 │
                 │ HTTPS
                 ▼
        ┌─────────────────┐
        │     NGINX       │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │    FASTAPI      │
        │   /api/v1       │
        └────────┬────────┘
                 │
        ┌────────┼───────────────┐
        │        │               │
        ▼        ▼               ▼
   PostgreSQL  Redis        Supabase Storage
    + PostGIS    │
                 ▼
           Celery Workers
                 │
                 ▼
             AI / ML
                 │
                 ▼
       Detection / Severity
       Prediction / Verification
                 │
                 ▼
            PostgreSQL
```

---

# 103. Final API Principles

The API must preserve the complete operational chain:

```text
WHO
 ↓
WHAT
 ↓
WHERE
 ↓
WHEN
 ↓
AI MODEL / VERSION
 ↓
HUMAN REVIEW
 ↓
MAINTENANCE
 ↓
REPAIR EVIDENCE
 ↓
VERIFICATION
 ↓
RECURRENCE
```

The API is not merely a CRUD interface.

It is the controlled integration layer connecting:

```text
Field Data
→ AI Analysis
→ Human Review
→ Road Intelligence
→ Maintenance
→ Repair
→ Verification
→ Historical Intelligence
```

The REST API must therefore prioritize **traceability, authorization, reliability, idempotency, explainability, and historical preservation** over convenience shortcuts.

---

## Document Status

**Document:** `07_API_SPECIFICATION.md`  
**Status:** Approved Baseline  
**Next Document:** `08_AI_ML_SPECIFICATION.md`