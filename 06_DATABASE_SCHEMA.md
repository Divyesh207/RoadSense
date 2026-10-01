# DATABASE_SCHEMA.md

# Road Intelligence & Pothole Management Platform

**Project Name:** Road Intelligence & Pothole Management Platform  
**Document Type:** Database Schema & Data Model Specification  
**Version:** 1.0  
**Status:** Approved Database Baseline  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`, `SRS.md`, `SYSTEM_ARCHITECTURE.md`, `TECH_STACK.md`  
**Last Updated:** October 2026

---

# 1. Purpose

This document defines the authoritative database architecture for the Road Intelligence & Pothole Management Platform.

It specifies:

- Database technology
- Extensions
- Data ownership
- Multi-organization structure
- Entities
- Relationships
- Columns
- Data types
- Constraints
- Indexing
- Geospatial storage
- AI result persistence
- Historical data preservation
- Maintenance and repair relationships
- Audit logging
- Job tracking
- Data lifecycle
- Migration strategy

This document is intended to be consumed by:

- Backend developers
- Database developers
- AI/ML developers
- QA engineers
- DevOps engineers
- Coding agents

The implementation must not invent a different database architecture without an approved architecture change.

---

# 2. Database Technology

The authoritative production database is:

```text
PostgreSQL
```

Managed initially through:

```text
Supabase PostgreSQL
```

Geospatial functionality:

```text
PostGIS
```

ORM:

```text
SQLAlchemy 2.x
```

Migration system:

```text
Alembic
```

---

# 3. Database Principles

The database must follow these principles:

1. PostgreSQL is the authoritative source of structured application state.
2. PostgreSQL must not store large media blobs.
3. Large media belongs in Supabase Storage.
4. All tenant-owned records must be organization-scoped.
5. Historical AI results must be preserved.
6. AI model/version metadata must be retained.
7. Foreign-key relationships must be enforced.
8. Important state transitions must be controlled.
9. Geospatial columns must use PostGIS.
10. Timestamps must be timezone-aware.
11. IDs should use UUIDs.
12. Database migrations must be version controlled.
13. Destructive schema changes require explicit migration review.
14. Clients must never connect directly to privileged PostgreSQL credentials.

---

# 4. PostgreSQL Extensions

The production database should enable:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

## 4.1 PostGIS

Used for:

- Road geometry
- Road segment geometry
- Inspection locations
- Damage locations
- Maintenance locations
- Repair locations
- Spatial searches
- Road-segment association
- Recurrence analysis

## 4.2 pgcrypto

Used for:

```text
gen_random_uuid()
```

for UUID generation.

---

# 5. Identifier Strategy

Primary identifiers should use:

```text
UUID
```

Example:

```text
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

UUIDs are preferred because:

- They are difficult to guess.
- They work well across offline clients.
- They support distributed processing.
- They reduce dependence on sequential identifiers.
- They simplify synchronization.

---

# 6. Timestamp Strategy

All authoritative timestamps must use:

```text
TIMESTAMPTZ
```

Examples:

```text
created_at
updated_at
submitted_at
processed_at
completed_at
reviewed_at
```

Application servers should store timestamps in UTC.

Clients may display timestamps in local time.

---

# 7. Organization / Multi-Tenant Model

The platform supports multiple organizations.

Primary structure:

```text
Organization
    │
    ├── Users
    ├── Roads
    ├── Inspections
    ├── Damage
    ├── Maintenance
    └── Reports
```

A user may belong to one or more organizations through memberships.

Conceptually:

```text
users
  │
  ▼
organization_memberships
  │
  ▼
organizations
```

Organization ownership must be explicitly represented for tenant-owned records.

---

# 8. High-Level Entity Model

The database consists of these major domains:

```text
IDENTITY
├── organizations
├── users
├── roles
├── permissions
├── role_permissions
└── organization_memberships

ROAD
├── roads
└── road_segments

INSPECTION
├── inspections
├── inspection_media
└── processing_jobs

AI
├── ai_models
├── ai_processing_runs
├── ai_detections
├── damage_records
└── damage_reviews

INTELLIGENCE
├── road_health_snapshots
├── maintenance_priority_snapshots
└── deterioration_predictions

MAINTENANCE
├── maintenance_jobs
├── maintenance_damage_links
├── repair_evidence
└── repair_verifications

HISTORY
├── recurrence_records
├── notifications
├── generated_reports
└── audit_logs
```

---

# 9. Entity Relationship Overview

```text
organizations
      │
      ├──────────────┐
      │              │
      ▼              ▼
    users      organization_memberships
                     │
                     ▼
                   roles
                     │
                     ▼
               permissions

organizations
      │
      ├──────────────► roads
      │                  │
      │                  ▼
      │            road_segments
      │                  │
      │        ┌─────────┼─────────┐
      │        │         │         │
      ▼        ▼         ▼         ▼
 inspections  damage  health   predictions
      │        │
      ▼        │
inspection_media
      │
      ▼
processing_jobs
      │
      ▼
ai_processing_runs
      │
      ▼
ai_detections
      │
      ▼
damage_records
      │
      ├──────────────► damage_reviews
      │
      ▼
maintenance_jobs
      │
      ├──────────────► maintenance_damage_links
      │
      ▼
repair_evidence
      │
      ▼
repair_verifications
      │
      ▼
recurrence_records
```

---

# 10. Database Naming Conventions

Tables use:

```text
snake_case
plural nouns
```

Examples:

```text
users
roads
road_segments
maintenance_jobs
```

Columns use:

```text
snake_case
```

Foreign keys use:

```text
<entity>_id
```

Examples:

```text
organization_id
road_id
inspection_id
maintenance_job_id
```

---

# 11. Standard Columns

Most persistent entities should include:

```text
id
created_at
updated_at
```

Tenant-owned entities should additionally include:

```text
organization_id
```

Historical/operational records should generally not be hard deleted.

---

# 12. Identity Domain

# 12.1 `organizations`

Represents an authority, municipality, road agency, contractor organization, or other tenant.

### Columns

| Column | Type | Null | Default | Description |
|---|---|---:|---|---|
| id | UUID | No | UUID | Primary key |
| name | VARCHAR(200) | No | — | Organization name |
| code | VARCHAR(50) | No | — | Unique organization code |
| organization_type | VARCHAR(50) | No | — | Authority, contractor, agency, etc. |
| email | VARCHAR(255) | Yes | — | Contact email |
| phone | VARCHAR(30) | Yes | — | Contact phone |
| address | TEXT | Yes | — | Organization address |
| is_active | BOOLEAN | No | TRUE | Active status |
| created_at | TIMESTAMPTZ | No | NOW() | Creation timestamp |
| updated_at | TIMESTAMPTZ | No | NOW() | Last update |

### Constraints

```text
PRIMARY KEY (id)
UNIQUE (code)
```

---

# 12.2 `users`

Represents authenticated platform users.

### Columns

| Column | Type | Null | Description |
|---|---|---:|---|
| id | UUID | No | User ID |
| email | VARCHAR(255) | No | Login email |
| password_hash | TEXT | No | bcrypt password hash |
| full_name | VARCHAR(150) | No | User name |
| phone | VARCHAR(30) | Yes | Phone |
| is_active | BOOLEAN | No | Account status |
| last_login_at | TIMESTAMPTZ | Yes | Last successful login |
| created_at | TIMESTAMPTZ | No | Creation |
| updated_at | TIMESTAMPTZ | No | Update |

### Constraints

Email uniqueness should be case-insensitive.

Recommended index:

```text
UNIQUE INDEX users_email_lower_idx
ON users (LOWER(email))
```

Passwords must never be stored in plaintext.

---

# 12.3 `roles`

Defines platform roles.

Initial roles:

```text
ADMINISTRATOR
AUTHORITY
INSPECTOR
CONTRACTOR
```

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| code | VARCHAR(50) | No |
| name | VARCHAR(100) | No |
| description | TEXT | Yes |
| is_system_role | BOOLEAN | No |
| is_active | BOOLEAN | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Constraints

```text
UNIQUE(code)
```

Roles are referenced by organization memberships.

---

# 12.4 `permissions`

Defines granular platform permissions.

Examples:

```text
roads.read
roads.write
inspections.create
inspections.read
damage.review
maintenance.create
maintenance.assign
repair.submit
verification.review
reports.generate
users.manage
audit.read
```

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| code | VARCHAR(100) | No |
| name | VARCHAR(150) | No |
| description | TEXT | Yes |
| resource | VARCHAR(50) | No |
| action | VARCHAR(50) | No |
| created_at | TIMESTAMPTZ | No |

### Constraints

```text
UNIQUE(code)
```

---

# 12.5 `role_permissions`

Many-to-many relationship between roles and permissions.

### Columns

| Column | Type | Null |
|---|---|---:|
| role_id | UUID | No |
| permission_id | UUID | No |

### Constraints

```text
PRIMARY KEY (role_id, permission_id)
FOREIGN KEY role_id → roles.id
FOREIGN KEY permission_id → permissions.id
```

---

# 12.6 `organization_memberships`

Associates users with organizations and roles.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| user_id | UUID | No |
| role_id | UUID | No |
| status | VARCHAR(30) | No |
| joined_at | TIMESTAMPTZ | No |
| invited_by_user_id | UUID | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Status

```text
INVITED
ACTIVE
SUSPENDED
REMOVED
```

### Constraints

A user should have one active membership for a given organization/role combination unless multiple role assignments are intentionally supported.

---

# 13. Road Domain

# 13.1 `roads`

Represents an authoritative road.

### Columns

| Column | Type | Null | Description |
|---|---|---:|---|
| id | UUID | No | Road ID |
| organization_id | UUID | No | Owning organization |
| name | VARCHAR(255) | No | Road name |
| road_code | VARCHAR(100) | Yes | External/internal road identifier |
| road_type | VARCHAR(50) | Yes | Road category |
| administrative_area | VARCHAR(150) | Yes | Administrative region |
| description | TEXT | Yes | Description |
| geometry | geometry(LineString,4326) | Yes | Road geometry |
| is_active | BOOLEAN | No | Active status |
| created_at | TIMESTAMPTZ | No | Creation |
| updated_at | TIMESTAMPTZ | No | Update |

### Constraints

```text
geometry must use SRID 4326
```

### Indexes

```text
INDEX roads_organization_idx
INDEX roads_code_idx
GIST INDEX roads_geometry_gist
```

---

# 13.2 `road_segments`

Represents a manageable portion of a road.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| road_id | UUID | No |
| segment_number | INTEGER | No |
| name | VARCHAR(150) | Yes |
| start_chainage | NUMERIC(12,3) | Yes |
| end_chainage | NUMERIC(12,3) | Yes |
| length_meters | NUMERIC(12,3) | Yes |
| geometry | geometry(LineString,4326) | Yes |
| is_active | BOOLEAN | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Constraints

```text
UNIQUE(road_id, segment_number)
CHECK(segment_number > 0)
CHECK(length_meters IS NULL OR length_meters >= 0)
```

### Indexes

```text
INDEX road_segments_organization_idx
INDEX road_segments_road_idx
GIST INDEX road_segments_geometry_gist
```

---

# 14. Inspection Domain

# 14.1 `inspections`

Represents an observation/inspection event.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| inspector_user_id | UUID | No |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| status | VARCHAR(40) | No |
| source | VARCHAR(30) | No |
| captured_at | TIMESTAMPTZ | Yes |
| submitted_at | TIMESTAMPTZ | Yes |
| location | geometry(Point,4326) | Yes |
| gps_accuracy_meters | NUMERIC(10,3) | Yes |
| notes | TEXT | Yes |
| failure_code | VARCHAR(100) | Yes |
| failure_message | TEXT | Yes |
| client_inspection_id | UUID | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Source

```text
ANDROID
WEB
MANUAL
IMPORT
```

### Status

```text
DRAFT
SUBMITTED
UPLOADING
PROCESSING
ANALYZED
REVIEW_REQUIRED
REVIEWED
COMPLETED
UPLOAD_FAILED
PROCESSING_FAILED
ANALYSIS_FAILED
```

### Constraints

```text
gps_accuracy_meters >= 0
```

Latitude/longitude validation is handled by PostGIS geometry creation and API validation.

### Indexes

```text
INDEX inspections_organization_idx
INDEX inspections_inspector_idx
INDEX inspections_road_idx
INDEX inspections_segment_idx
INDEX inspections_status_idx
INDEX inspections_captured_at_idx
GIST INDEX inspections_location_gist
```

---

# 14.2 `inspection_media`

Stores metadata for inspection media.

Actual binary data belongs in Supabase Storage.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| inspection_id | UUID | No |
| media_type | VARCHAR(20) | No |
| storage_bucket | VARCHAR(100) | No |
| storage_path | TEXT | No |
| original_filename | VARCHAR(255) | Yes |
| mime_type | VARCHAR(100) | No |
| file_size_bytes | BIGINT | Yes |
| checksum | VARCHAR(128) | Yes |
| captured_at | TIMESTAMPTZ | Yes |
| uploaded_at | TIMESTAMPTZ | Yes |
| location | geometry(Point,4326) | Yes |
| duration_seconds | NUMERIC(12,3) | Yes |
| width_px | INTEGER | Yes |
| height_px | INTEGER | Yes |
| frame_rate | NUMERIC(8,3) | Yes |
| upload_status | VARCHAR(30) | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Media types

```text
IMAGE
VIDEO
```

### Upload status

```text
PENDING
UPLOADING
UPLOADED
FAILED
DELETED
```

### Constraints

```text
file_size_bytes >= 0
duration_seconds >= 0
width_px > 0 where provided
height_px > 0 where provided
```

---

# 15. Background Processing

# 15.1 `processing_jobs`

Tracks asynchronous processing.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| job_type | VARCHAR(60) | No |
| entity_type | VARCHAR(60) | No |
| entity_id | UUID | No |
| idempotency_key | VARCHAR(255) | No |
| status | VARCHAR(30) | No |
| priority | INTEGER | No |
| attempts | INTEGER | No |
| max_attempts | INTEGER | No |
| worker_version | VARCHAR(100) | Yes |
| queued_at | TIMESTAMPTZ | No |
| started_at | TIMESTAMPTZ | Yes |
| completed_at | TIMESTAMPTZ | Yes |
| failed_at | TIMESTAMPTZ | Yes |
| error_code | VARCHAR(100) | Yes |
| error_message | TEXT | Yes |
| result_metadata | JSONB | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Job types

```text
PROCESS_INSPECTION
RUN_DAMAGE_DETECTION
PROCESS_VIDEO
CALCULATE_ROAD_HEALTH
CALCULATE_PRIORITY
GENERATE_PREDICTION
VERIFY_REPAIR
CALCULATE_RECURRENCE
GENERATE_REPORT
SEND_NOTIFICATION
```

### Status

```text
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLED
```

### Constraints

```text
attempts >= 0
max_attempts >= 1
priority >= 0
```

### Idempotency

Recommended unique constraint:

```text
UNIQUE(organization_id, job_type, idempotency_key)
```

---

# 16. AI Model Registry

# 16.1 `ai_models`

Stores metadata about AI/ML models.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | Yes |
| name | VARCHAR(150) | No |
| model_family | VARCHAR(100) | No |
| model_type | VARCHAR(50) | No |
| version | VARCHAR(50) | No |
| artifact_uri | TEXT | No |
| artifact_checksum | VARCHAR(128) | Yes |
| dataset_version | VARCHAR(100) | Yes |
| configuration_version | VARCHAR(100) | Yes |
| framework | VARCHAR(100) | Yes |
| status | VARCHAR(30) | No |
| metrics | JSONB | Yes |
| metadata | JSONB | Yes |
| trained_at | TIMESTAMPTZ | Yes |
| deployed_at | TIMESTAMPTZ | Yes |
| retired_at | TIMESTAMPTZ | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Model types

```text
DETECTION
SEVERITY
PREDICTION
VERIFICATION
CLASSIFICATION
```

### Status

```text
CANDIDATE
ACTIVE
DISABLED
RETIRED
```

### Constraints

```text
UNIQUE(name, version)
```

Model artifacts are stored outside PostgreSQL.

---

# 16.2 `ai_processing_runs`

Represents a specific execution of an AI model.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| processing_job_id | UUID | Yes |
| model_id | UUID | No |
| inspection_id | UUID | Yes |
| media_id | UUID | Yes |
| run_type | VARCHAR(50) | No |
| configuration_version | VARCHAR(100) | Yes |
| confidence_threshold | NUMERIC(6,5) | Yes |
| input_metadata | JSONB | Yes |
| output_metadata | JSONB | Yes |
| status | VARCHAR(30) | No |
| started_at | TIMESTAMPTZ | Yes |
| completed_at | TIMESTAMPTZ | Yes |
| error_message | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |

### Run types

```text
DETECTION
SEVERITY
PREDICTION
VERIFICATION
VIDEO_PROCESSING
```

---

# 17. Damage Domain

# 17.1 `damage_types`

Extensible catalog of supported damage classes.

### Initial records

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| code | VARCHAR(50) | No |
| name | VARCHAR(100) | No |
| description | TEXT | Yes |
| is_active | BOOLEAN | No |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Constraint

```text
UNIQUE(code)
```

This table prevents damage classes from being hard-coded across the application.

---

# 17.2 `ai_detections`

Stores raw/model-generated detection output.

This table is intentionally separate from reviewed damage records.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| ai_processing_run_id | UUID | No |
| inspection_id | UUID | No |
| media_id | UUID | No |
| damage_type_id | UUID | No |
| frame_number | INTEGER | Yes |
| frame_timestamp_ms | BIGINT | Yes |
| confidence | NUMERIC(7,6) | No |
| bbox_x_min | NUMERIC(10,7) | No |
| bbox_y_min | NUMERIC(10,7) | No |
| bbox_x_max | NUMERIC(10,7) | No |
| bbox_y_max | NUMERIC(10,7) | No |
| pixel_width | INTEGER | Yes |
| pixel_height | INTEGER | Yes |
| location | geometry(Point,4326) | Yes |
| raw_output | JSONB | Yes |
| created_at | TIMESTAMPTZ | No |

### Bounding-box convention

For normalized coordinates:

```text
0.0 ≤ x_min < x_max ≤ 1.0
0.0 ≤ y_min < y_max ≤ 1.0
```

### Confidence

```text
0.0 ≤ confidence ≤ 1.0
```

### Indexes

```text
INDEX ai_detections_inspection_idx
INDEX ai_detections_media_idx
INDEX ai_detections_run_idx
INDEX ai_detections_damage_type_idx
GIST INDEX ai_detections_location_gist
```

---

# 17.3 `damage_records`

Represents the operational/canonical damage entity.

An AI detection can create a damage record, but the raw detection remains unchanged.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| inspection_id | UUID | No |
| source_detection_id | UUID | Yes |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| damage_type_id | UUID | No |
| source_type | VARCHAR(30) | No |
| severity | VARCHAR(20) | No |
| severity_score | NUMERIC(7,4) | Yes |
| severity_method_version | VARCHAR(100) | Yes |
| location | geometry(Point,4326) | Yes |
| status | VARCHAR(30) | No |
| confidence | NUMERIC(7,6) | Yes |
| estimated_area_m2 | NUMERIC(14,4) | Yes |
| detected_at | TIMESTAMPTZ | Yes |
| reviewed_at | TIMESTAMPTZ | Yes |
| reviewed_by_user_id | UUID | Yes |
| notes | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Source types

```text
AI
MANUAL
IMPORT
```

### Severity

```text
LOW
MEDIUM
HIGH
CRITICAL
```

### Status

```text
DETECTED
UNDER_REVIEW
CONFIRMED
REJECTED
RESOLVED
```

### Constraints

```text
confidence BETWEEN 0 AND 1
severity_score BETWEEN 0 AND 100 where provided
estimated_area_m2 >= 0 where provided
```

---

# 17.4 `damage_reviews`

Stores human review actions separately from AI results.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| damage_record_id | UUID | No |
| reviewer_user_id | UUID | No |
| review_status | VARCHAR(30) | No |
| original_damage_type_id | UUID | Yes |
| reviewed_damage_type_id | UUID | Yes |
| original_severity | VARCHAR(20) | Yes |
| reviewed_severity | VARCHAR(20) | Yes |
| original_confidence | NUMERIC(7,6) | Yes |
| review_notes | TEXT | Yes |
| reviewed_at | TIMESTAMPTZ | No |
| created_at | TIMESTAMPTZ | No |

### Review status

```text
CONFIRMED
REJECTED
CORRECTED
```

Historical review records should be retained.

---

# 18. Road Intelligence

# 18.1 `road_health_snapshots`

Stores calculated road/segment health at a point in time.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| health_score | NUMERIC(6,2) | Yes |
| health_status | VARCHAR(30) | No |
| calculation_version | VARCHAR(100) | No |
| input_data_timestamp | TIMESTAMPTZ | Yes |
| factors | JSONB | No |
| calculation_metadata | JSONB | Yes |
| calculated_at | TIMESTAMPTZ | No |
| created_at | TIMESTAMPTZ | No |

### Health score

If present:

```text
0 ≤ health_score ≤ 100
```

### Important rule

Insufficient data must not be converted into a fake score.

Recommended status:

```text
INSUFFICIENT_DATA
```

Other statuses may include:

```text
GOOD
FAIR
POOR
CRITICAL
```

The exact thresholds will be defined in the AI/analytics specification.

---

# 18.2 `maintenance_priority_snapshots`

Stores calculated maintenance priority.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| priority_score | NUMERIC(6,2) | Yes |
| priority_level | VARCHAR(30) | No |
| calculation_version | VARCHAR(100) | No |
| factors | JSONB | No |
| input_data_timestamp | TIMESTAMPTZ | Yes |
| calculated_at | TIMESTAMPTZ | No |
| created_at | TIMESTAMPTZ | No |

### Priority score

If used:

```text
0 ≤ priority_score ≤ 100
```

The score must always be accompanied by its contributing factors.

---

# 18.3 `deterioration_predictions`

Stores historical prediction results.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| model_id | UUID | No |
| prediction_horizon_days | INTEGER | No |
| target_type | VARCHAR(60) | No |
| predicted_value | NUMERIC(14,6) | Yes |
| predicted_risk | NUMERIC(6,2) | Yes |
| uncertainty_lower | NUMERIC(14,6) | Yes |
| uncertainty_upper | NUMERIC(14,6) | Yes |
| confidence | NUMERIC(7,6) | Yes |
| feature_version | VARCHAR(100) | Yes |
| features | JSONB | No |
| input_data_timestamp | TIMESTAMPTZ | Yes |
| generated_at | TIMESTAMPTZ | No |
| status | VARCHAR(30) | No |
| created_at | TIMESTAMPTZ | No |

### Status

```text
GENERATED
INSUFFICIENT_DATA
INVALIDATED
```

### Constraints

```text
prediction_horizon_days > 0
confidence BETWEEN 0 AND 1 where provided
predicted_risk BETWEEN 0 AND 100 where provided
```

Predictions remain historical records.

---

# 19. Maintenance Domain

# 19.1 `maintenance_jobs`

Represents an operational maintenance task.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| road_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| created_by_user_id | UUID | No |
| assigned_to_user_id | UUID | Yes |
| assigned_to_organization_id | UUID | Yes |
| title | VARCHAR(255) | No |
| description | TEXT | Yes |
| priority_level | VARCHAR(30) | No |
| priority_score | NUMERIC(6,2) | Yes |
| status | VARCHAR(40) | No |
| due_at | TIMESTAMPTZ | Yes |
| started_at | TIMESTAMPTZ | Yes |
| completed_at | TIMESTAMPTZ | Yes |
| verified_at | TIMESTAMPTZ | Yes |
| location | geometry(Point,4326) | Yes |
| completion_notes | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Status

```text
OPEN
ASSIGNED
IN_PROGRESS
COMPLETED
VERIFICATION_PENDING
VERIFIED
REJECTED
CANCELLED
```

### Priority

```text
LOW
MEDIUM
HIGH
CRITICAL
```

### Constraints

```text
priority_score BETWEEN 0 AND 100 where provided
```

---

# 19.2 `maintenance_damage_links`

Many-to-many relationship between maintenance jobs and damage records.

### Columns

| Column | Type | Null |
|---|---|---:|
| maintenance_job_id | UUID | No |
| damage_record_id | UUID | No |
| relationship_type | VARCHAR(40) | No |
| created_at | TIMESTAMPTZ | No |

### Relationship types

```text
PRIMARY
RELATED
RECURRENCE
GROUPED
```

### Constraints

```text
PRIMARY KEY (maintenance_job_id, damage_record_id)
```

---

# 19.3 Maintenance Status History

Maintenance status history should be preserved.

Recommended table:

`maintenance_status_history`

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| maintenance_job_id | UUID | No |
| previous_status | VARCHAR(40) | Yes |
| new_status | VARCHAR(40) | No |
| changed_by_user_id | UUID | No |
| reason | TEXT | Yes |
| changed_at | TIMESTAMPTZ | No |

This allows the complete maintenance lifecycle to be reconstructed.

---

# 20. Repair Domain

# 20.1 `repair_evidence`

Stores metadata for before/after repair evidence.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| maintenance_job_id | UUID | No |
| uploaded_by_user_id | UUID | No |
| evidence_type | VARCHAR(30) | No |
| storage_bucket | VARCHAR(100) | No |
| storage_path | TEXT | No |
| media_type | VARCHAR(20) | No |
| mime_type | VARCHAR(100) | No |
| file_size_bytes | BIGINT | Yes |
| checksum | VARCHAR(128) | Yes |
| captured_at | TIMESTAMPTZ | Yes |
| location | geometry(Point,4326) | Yes |
| notes | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Evidence types

```text
BEFORE
DURING
AFTER
OTHER
```

### Media types

```text
IMAGE
VIDEO
DOCUMENT
```

---

# 20.2 `repair_verifications`

Stores AI and/or human repair verification results.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| maintenance_job_id | UUID | No |
| ai_processing_run_id | UUID | Yes |
| verified_by_user_id | UUID | Yes |
| verification_status | VARCHAR(40) | No |
| ai_confidence | NUMERIC(7,6) | Yes |
| comparison_metrics | JSONB | Yes |
| findings | JSONB | No |
| reviewer_notes | TEXT | Yes |
| verified_at | TIMESTAMPTZ | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Verification status

```text
PENDING
AI_PASSED
AI_FAILED
NEEDS_REVIEW
APPROVED
REJECTED
```

### Constraint

```text
ai_confidence BETWEEN 0 AND 1 where provided
```

Historical verification results must not be deleted simply because a later verification is created.

---

# 21. Recurrence Domain

# 21.1 `recurrence_records`

Represents a potential or confirmed recurrence relationship.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| historical_damage_id | UUID | No |
| new_damage_id | UUID | No |
| related_maintenance_job_id | UUID | Yes |
| related_repair_verification_id | UUID | Yes |
| road_segment_id | UUID | Yes |
| spatial_distance_meters | NUMERIC(12,3) | Yes |
| temporal_distance_days | INTEGER | Yes |
| similarity_score | NUMERIC(7,6) | Yes |
| recurrence_score | NUMERIC(7,6) | Yes |
| detection_method_version | VARCHAR(100) | Yes |
| status | VARCHAR(30) | No |
| evaluated_at | TIMESTAMPTZ | No |
| reviewed_by_user_id | UUID | Yes |
| reviewed_at | TIMESTAMPTZ | Yes |
| review_notes | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Status

```text
POTENTIAL
CONFIRMED
REJECTED
```

### Constraints

```text
spatial_distance_meters >= 0
similarity_score BETWEEN 0 AND 1 where provided
recurrence_score BETWEEN 0 AND 1 where provided
```

---

# 22. Notification Domain

# 22.1 `notifications`

Stores user-facing notifications.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| user_id | UUID | No |
| notification_type | VARCHAR(60) | No |
| title | VARCHAR(255) | No |
| message | TEXT | No |
| data | JSONB | Yes |
| read_at | TIMESTAMPTZ | Yes |
| created_at | TIMESTAMPTZ | No |

### Examples

```text
INSPECTION_COMPLETED
MAINTENANCE_ASSIGNED
REPAIR_SUBMITTED
VERIFICATION_REQUIRED
VERIFICATION_COMPLETED
RECURRENCE_DETECTED
```

### Indexes

```text
INDEX notifications_user_idx
INDEX notifications_unread_idx
INDEX notifications_created_at_idx
```

---

# 23. Reporting Domain

# 23.1 `generated_reports`

Tracks generated report files.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | No |
| requested_by_user_id | UUID | No |
| report_type | VARCHAR(60) | No |
| status | VARCHAR(30) | No |
| parameters | JSONB | No |
| storage_bucket | VARCHAR(100) | Yes |
| storage_path | TEXT | Yes |
| processing_job_id | UUID | Yes |
| generated_at | TIMESTAMPTZ | Yes |
| expires_at | TIMESTAMPTZ | Yes |
| error_message | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |
| updated_at | TIMESTAMPTZ | No |

### Status

```text
QUEUED
GENERATING
COMPLETED
FAILED
EXPIRED
```

---

# 24. Audit Domain

# 24.1 `audit_logs`

Stores important security and business actions.

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| organization_id | UUID | Yes |
| actor_user_id | UUID | Yes |
| action | VARCHAR(100) | No |
| entity_type | VARCHAR(80) | No |
| entity_id | UUID | Yes |
| request_id | VARCHAR(100) | Yes |
| before_data | JSONB | Yes |
| after_data | JSONB | Yes |
| metadata | JSONB | Yes |
| ip_address | INET | Yes |
| user_agent | TEXT | Yes |
| created_at | TIMESTAMPTZ | No |

### Examples

```text
USER_LOGIN
USER_DEACTIVATED
ROLE_CHANGED
INSPECTION_CREATED
DETECTION_REVIEWED
SEVERITY_CHANGED
MAINTENANCE_CREATED
MAINTENANCE_ASSIGNED
REPAIR_SUBMITTED
VERIFICATION_APPROVED
VERIFICATION_REJECTED
```

Audit records should be append-oriented.

---

# 25. Optional Session Security

If refresh-token-based JWT sessions are implemented, the database may include:

`refresh_tokens`

### Columns

| Column | Type | Null |
|---|---|---:|
| id | UUID | No |
| user_id | UUID | No |
| token_hash | TEXT | No |
| device_identifier | VARCHAR(255) | Yes |
| expires_at | TIMESTAMPTZ | No |
| revoked_at | TIMESTAMPTZ | Yes |
| created_at | TIMESTAMPTZ | No |
| last_used_at | TIMESTAMPTZ | Yes |

Raw refresh tokens must not be stored.

Only hashes should be persisted.

---

# 26. Foreign-Key Relationship Summary

Core relationships:

```text
organizations
 ├── organization_memberships
 ├── roads
 ├── road_segments
 ├── inspections
 ├── damage_records
 ├── maintenance_jobs
 └── audit_logs

users
 ├── organization_memberships
 ├── inspections
 ├── damage_reviews
 ├── maintenance_jobs
 ├── repair_evidence
 └── audit_logs

roads
 └── road_segments

inspections
 ├── inspection_media
 ├── ai_detections
 └── damage_records

inspection_media
 └── ai_detections

ai_models
 ├── ai_processing_runs
 └── deterioration_predictions

ai_processing_runs
 └── ai_detections

ai_detections
 └── damage_records

damage_records
 ├── damage_reviews
 ├── maintenance_damage_links
 └── recurrence_records

maintenance_jobs
 ├── maintenance_damage_links
 ├── maintenance_status_history
 ├── repair_evidence
 └── repair_verifications

repair_verifications
 └── recurrence_records
```

---

# 27. Delete Behavior

Historical integrity is more important than aggressive deletion.

## 27.1 Core historical records

The following should generally not be hard deleted:

```text
inspections
inspection_media metadata
ai_processing_runs
ai_detections
damage_records
damage_reviews
road_health_snapshots
deterioration_predictions
maintenance_jobs
repair_evidence
repair_verifications
recurrence_records
audit_logs
```

---

# 28. Soft Deletion

Master/configuration entities may use:

```text
is_active
```

instead of hard deletion.

Examples:

```text
users
organizations
roads
road_segments
damage_types
roles
permissions
ai_models
```

If actual soft deletion is required, a separate:

```text
deleted_at
```

may be added.

Historical foreign-key relationships must remain valid.

---

# 29. Organization Scoping

Every organization-owned operational table should include:

```text
organization_id
```

This includes:

```text
roads
road_segments
inspections
inspection_media
processing_jobs
ai_processing_runs
ai_detections
damage_records
damage_reviews
road_health_snapshots
maintenance_priority_snapshots
deterioration_predictions
maintenance_jobs
repair_evidence
repair_verifications
recurrence_records
notifications
generated_reports
audit_logs
```

This provides explicit tenant isolation and efficient filtering.

---

# 30. Organization Consistency

Application services must verify that related records belong to compatible organization scopes.

For example:

```text
Inspection.organization_id
      =
Damage.organization_id
      =
Maintenance.organization_id
```

Cross-organization relationships must be explicitly authorized.

The API must never rely only on a client-provided organization ID.

---

# 31. Geospatial Strategy

The authoritative spatial reference system is:

```text
SRID 4326
```

Initial geometry types:

```text
Road
    → LineString

Road Segment
    → LineString

Inspection
    → Point

Damage
    → Point

Maintenance
    → Point

Repair Evidence
    → Point
```

---

# 32. Spatial Indexing

All frequently queried geometry columns should use GiST indexes.

Examples:

```sql
CREATE INDEX roads_geometry_gist
ON roads
USING GIST (geometry);
```

Equivalent indexes should exist for:

```text
road_segments.geometry
inspections.location
ai_detections.location
damage_records.location
maintenance_jobs.location
repair_evidence.location
```

where spatial queries are required.

---

# 33. Road-Segment Association

The database stores both:

```text
road_id
road_segment_id
```

where relevant.

This avoids repeatedly resolving road hierarchy from geometry.

However, the backend must validate that:

```text
road_segment.road_id = road_id
```

before persisting the relationship.

---

# 34. Damage Location Strategy

A damage record may contain:

```text
location
road_id
road_segment_id
```

The geographic location is the observation location.

The road/segment relationship is the operational association.

These should remain separate concepts.

---

# 35. AI Bounding Box Strategy

Raw AI bounding boxes should remain in `ai_detections`.

Recommended normalized coordinate convention:

```text
x_min
y_min
x_max
y_max
```

with:

```text
0 ≤ coordinate ≤ 1
```

Pixel dimensions may additionally be stored when available.

This allows the original AI output to be reproduced or visualized.

---

# 36. JSONB Usage

JSONB is permitted for:

```text
AI raw outputs
AI metadata
Feature snapshots
Calculation factors
Report parameters
Notification metadata
Audit metadata
Model metrics
```

JSONB must not replace normal relational columns for frequently queried core attributes.

Bad:

```text
damage.data->>'severity'
```

as the only severity representation.

Preferred:

```text
damage_records.severity
```

with optional additional JSONB metadata.

---

# 37. Database Constraints

Important values must be constrained.

Examples:

### Confidence

```text
0 ≤ confidence ≤ 1
```

### Health

```text
0 ≤ health_score ≤ 100
```

### Priority

```text
0 ≤ priority_score ≤ 100
```

### GPS accuracy

```text
gps_accuracy_meters ≥ 0
```

### Bounding box

```text
x_min < x_max
y_min < y_max
```

### Prediction horizon

```text
prediction_horizon_days > 0
```

---

# 38. Unique Constraints

Important uniqueness rules include:

```text
organizations.code
users.lower(email)
roles.code
permissions.code
damage_types.code
roles + permissions
road_id + segment_number
organization + job_type + idempotency_key
```

Other uniqueness constraints should be added only when business semantics require them.

---

# 39. Index Strategy

The database should index:

## Identity

```text
users.email
organization_memberships.user_id
organization_memberships.organization_id
```

## Roads

```text
roads.organization_id
road_segments.organization_id
road_segments.road_id
```

## Inspections

```text
inspections.organization_id
inspections.status
inspections.inspector_user_id
inspections.captured_at
```

## AI

```text
processing_jobs.status
processing_jobs.job_type
processing_jobs.organization_id
ai_processing_runs.model_id
ai_detections.inspection_id
ai_detections.media_id
```

## Damage

```text
damage_records.organization_id
damage_records.road_segment_id
damage_records.severity
damage_records.status
damage_records.detected_at
```

## Maintenance

```text
maintenance_jobs.organization_id
maintenance_jobs.status
maintenance_jobs.assigned_to_user_id
maintenance_jobs.due_at
```

## Notifications

```text
notifications.user_id
notifications.read_at
notifications.created_at
```

---

# 40. Composite Indexes

Frequently filtered tenant queries should use composite indexes where justified.

Examples:

```text
(organization_id, status)
(organization_id, created_at)
(organization_id, road_segment_id)
(organization_id, severity)
```

Indexes should be added based on actual query patterns rather than indiscriminately.

---

# 41. Transaction Boundaries

Operations requiring multiple related writes must use database transactions.

Example:

```text
Create Maintenance Job
       +
Link Damage
       +
Create Audit Record
```

must either:

```text
ALL SUCCESS
```

or:

```text
ALL ROLLED BACK
```

where atomicity is required.

---

# 42. Inspection Transaction Example

Creating an inspection may involve:

```text
1. Create inspection
2. Create media metadata
3. Create processing job
4. Create audit record
```

If these records must be atomic, they should be committed together.

Actual media upload may occur outside the database transaction because object storage is a separate system.

---

# 43. Media Upload Consistency

Object storage and PostgreSQL cannot rely on one native transaction.

The system should use an explicit upload state:

```text
PENDING
 ↓
UPLOADING
 ↓
UPLOADED
```

If object upload fails:

```text
FAILED
```

The corresponding database record must not be represented as successfully uploaded.

---

# 44. AI Processing Consistency

AI processing should follow:

```text
Job Created
    ↓
QUEUED
    ↓
RUNNING
    ↓
Persist Results
    ↓
COMPLETED
```

The worker must not mark a job `COMPLETED` before required result persistence succeeds.

---

# 45. AI Reprocessing

The database must support processing the same media with multiple model versions.

Example:

```text
Media 001
 │
 ├── AI Run v1.0
 │      └── Detection results
 │
 └── AI Run v2.0
        └── Detection results
```

Previous results remain available.

A model update must never require destructive deletion of previous results.

---

# 46. Canonical Damage Record

The platform distinguishes:

```text
AI Detection
        ↓
Damage Record
        ↓
Human Review
```

`ai_detections` represents what the model observed.

`damage_records` represents the operational damage entity.

`damage_reviews` represents human review/correction.

This separation is mandatory for traceability.

---

# 47. Road Health History

Road health should be stored as snapshots rather than overwriting one current value.

Example:

```text
Segment A

01 Oct → Health 72
15 Oct → Health 65
01 Nov → Health 58
15 Nov → Health 51
```

This enables:

- Trend analysis
- Prediction features
- Historical reports
- Deterioration analysis

---

# 48. Maintenance History

Maintenance status changes must be traceable.

Example:

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

`maintenance_status_history` preserves the transition history.

---

# 49. Prediction History

Predictions must not overwrite one another.

Each prediction is a separate historical record.

Example:

```text
Segment A
 ├── Prediction 01
 ├── Prediction 02
 └── Prediction 03
```

This allows later model evaluation.

---

# 50. Audit History

Audit logs are append-oriented.

Application code should not expose normal user operations for deleting audit entries.

Administrative access to audit data must be restricted.

---

# 51. Database Security

Database credentials must exist only on trusted server infrastructure.

Never expose:

```text
DATABASE_URL
database password
Supabase service-role key
```

to:

```text
Browser
Android application
public JavaScript
```

---

# 52. Supabase Usage

Supabase provides:

```text
PostgreSQL
PostGIS
Storage
```

The application's business logic remains in FastAPI.

The clients must not depend on Supabase database APIs for core application behavior.

---

# 53. Row-Level Security Consideration

Because the architecture uses:

```text
Client
 ↓
FastAPI
 ↓
PostgreSQL
```

application-level authorization is the primary security boundary.

If Supabase Row-Level Security is enabled, it should be treated as an additional defense-in-depth layer.

RLS policies must not contradict backend organization and role authorization.

The final RLS strategy will be documented in `SECURITY.md`.

---

# 54. Database Migration Strategy

All schema changes must use Alembic migrations.

Example:

```text
Migration 001
Initial schema

Migration 002
Add road segments

Migration 003
Add AI model registry

Migration 004
Add repair verification
```

Migrations must be committed to Git.

---

# 55. Migration Rules

## DB-MIG-001

Never manually modify production schema without a migration.

## DB-MIG-002

Every migration must be reversible where practical.

## DB-MIG-003

Destructive changes require explicit review.

## DB-MIG-004

Data migrations must be separated logically from schema-only changes where appropriate.

## DB-MIG-005

Production migrations must be tested against a staging database.

---

# 56. Seed Data

Development seed data may include:

```text
Roles
Permissions
Damage Types
Demo Organization
Demo Users
Sample Roads
Sample Segments
```

Production seed operations must never overwrite real records.

System reference data should be deterministic.

---

# 57. Reference Data

The following should be treated as controlled reference data:

```text
Roles
Permissions
Damage Types
Workflow values
```

Where PostgreSQL enum types are not used, stable string codes should be used.

Example:

```text
POTHOLE
CRACK
DEPRESSION
```

The code must remain stable even if the display name changes.

---

# 58. State Machine Enforcement

Workflow transitions should primarily be enforced by the application service layer.

Example:

```text
OPEN
 ↓
ASSIGNED
```

is valid.

But:

```text
OPEN
 ↓
VERIFIED
```

should be rejected unless the defined transition rules explicitly permit it.

Database constraints should provide basic integrity, while business transition logic belongs in backend services.

---

# 59. Concurrency Control

Concurrent updates must not silently overwrite important state.

Examples:

```text
Two users updating maintenance status
Two reviewers editing damage
Two workers processing the same job
```

The backend should use appropriate:

- Transactions
- Row locking
- Optimistic concurrency/version fields
- Idempotency keys

where necessary.

---

# 60. Duplicate Prevention

Duplicate creation must be controlled for:

```text
Android inspections
Media uploads
Processing jobs
AI processing retries
Maintenance actions
Notifications
```

The combination of:

```text
client-generated UUID
+
idempotency key
+
database constraints
```

should be used where appropriate.

---

# 61. Offline UUID Strategy

Android should generate stable UUIDs locally for offline-created inspections.

Example:

```text
Device
 ↓
Generate UUID
 ↓
Create LOCAL_DRAFT
 ↓
Queue
 ↓
Upload
 ↓
Backend uses same UUID
```

This prevents the same inspection from being created multiple times after retry.

---

# 62. Data Retention

Historical records should be retained according to organizational and legal requirements.

Initial technical policy:

```text
Do not automatically delete operational history.
```

Retention policies may later be implemented for:

- Temporary processing artifacts
- Expired reports
- Old notification data
- Obsolete media

Retention rules must not accidentally delete evidence required for historical road intelligence.

---

# 63. Media Retention

Media retention should be configurable by organization/policy.

Potential categories:

```text
Inspection Media
Repair Evidence
Generated Reports
Model Artifacts
```

Before deleting media, the system must determine whether the media is referenced by historical or audit records.

---

# 64. Database Backup

Production PostgreSQL backups must be provided through the managed database strategy.

The deployment documentation must define:

- Backup frequency
- Recovery expectations
- Restoration procedure
- Backup verification

The application must not assume that database backups are automatically sufficient without restoration testing.

---

# 65. Disaster Recovery Considerations

Critical structured data:

```text
PostgreSQL
```

Critical media:

```text
Supabase Storage
```

Critical configuration:

```text
Git
+
Environment secret management
+
Model artifact storage
```

A complete recovery plan must restore all three categories.

---

# 66. Performance Considerations

The schema should support:

- Pagination
- Date filtering
- Organization filtering
- Road filtering
- Segment filtering
- Severity filtering
- Status filtering
- Spatial searches

Large tables must be monitored for query performance.

---

# 67. Spatial Query Examples

The database must support operations such as:

```text
Find damage within 50 meters of a point.

Find road segments near an inspection.

Find historical damage within a recurrence radius.

Find all high-severity damage on a road.

Find maintenance jobs within a geographic region.
```

PostGIS spatial indexes should be used where appropriate.

---

# 68. Example Spatial Relationship

Conceptually:

```text
New Damage
     ●
     │
     │ spatial distance
     ▼
Historical Damage
     ●
```

The recurrence engine can use:

```text
ST_DWithin()
```

or equivalent spatial operations.

The exact recurrence threshold belongs to the AI/ML specification.

---

# 69. Data Flow Through Database

The canonical persistence flow is:

```text
Inspection
   ↓
Inspection Media
   ↓
Processing Job
   ↓
AI Processing Run
   ↓
AI Detection
   ↓
Damage Record
   ↓
Damage Review
   ↓
Road Health Snapshot
   ↓
Maintenance Priority
   ↓
Maintenance Job
   ↓
Repair Evidence
   ↓
Repair Verification
   ↓
Recurrence Record
```

---

# 70. Database-to-API Boundary

API schemas must not simply expose database tables directly.

The backend should use:

```text
Database Models
      ↓
Service Layer
      ↓
Pydantic DTOs
      ↓
API Response
```

This prevents database structure from becoming an accidental public API contract.

---

# 71. Database-to-AI Boundary

The AI worker should receive explicit processing inputs.

It should not arbitrarily query the entire database.

Example:

```text
Processing Job
    ↓
Authorized Input IDs
    ↓
Required Media
    ↓
Required Context
    ↓
Model
    ↓
Structured Result
```

This improves reproducibility and security.

---

# 72. AI Result Integrity

Every AI-generated result must be traceable to:

```text
Input
+
Model
+
Version
+
Configuration
+
Execution
```

For detection:

```text
inspection_id
media_id
ai_processing_run_id
model_id
```

must be available.

---

# 73. Historical Model Results

Example:

```text
Model v1.0
    ↓
Detection A

Model v2.0
    ↓
Detection B
```

Neither result should be silently deleted.

The application may identify one result as:

```text
CURRENT_REVIEWED_RESULT
```

while preserving previous results.

---

# 74. Database Documentation Requirements

Every new table introduced after this document must document:

```text
Purpose
Owner
Primary Key
Foreign Keys
Columns
Constraints
Indexes
Retention
Security Scope
```

---

# 75. SQLAlchemy Model Rules

SQLAlchemy models should:

- Use explicit relationships.
- Define foreign keys.
- Define indexes.
- Define constraints.
- Use timezone-aware timestamps.
- Avoid hidden database behavior.
- Match Alembic migrations.
- Avoid embedding business workflows inside ORM models.

---

# 76. Alembic Rules

Alembic migrations must be:

```text
Version controlled
Reviewable
Testable
Ordered
Environment-aware
```

The migration history is part of the source code.

---

# 77. Database Testing

Database tests must verify:

```text
Foreign keys
Unique constraints
Check constraints
Spatial columns
Organization isolation
State persistence
Transaction rollback
Idempotency
Migration correctness
```

---

# 78. Critical Database Invariants

The following must always remain true.

### INV-DB-001

Every inspection belongs to an organization.

### INV-DB-002

Every damage record belongs to an inspection.

### INV-DB-003

Every AI detection identifies its processing run.

### INV-DB-004

Every AI processing run identifies its model/version.

### INV-DB-005

Every maintenance job preserves its organization scope.

### INV-DB-006

Repair evidence belongs to a maintenance job.

### INV-DB-007

Repair verification belongs to a maintenance job.

### INV-DB-008

Historical AI results are not silently deleted.

### INV-DB-009

Organization boundaries are enforced.

### INV-DB-010

Client applications never receive privileged database credentials.

---

# 79. Recommended Table Inventory

The initial production schema should contain approximately:

```text
IDENTITY
1. organizations
2. users
3. roles
4. permissions
5. role_permissions
6. organization_memberships
7. refresh_tokens          [if refresh-token strategy is used]

ROAD
8. roads
9. road_segments

INSPECTION
10. inspections
11. inspection_media

JOBS
12. processing_jobs

AI
13. ai_models
14. ai_processing_runs
15. damage_types
16. ai_detections
17. damage_records
18. damage_reviews

INTELLIGENCE
19. road_health_snapshots
20. maintenance_priority_snapshots
21. deterioration_predictions

MAINTENANCE
22. maintenance_jobs
23. maintenance_damage_links
24. maintenance_status_history

REPAIR
25. repair_evidence
26. repair_verifications

HISTORY
27. recurrence_records
28. notifications
29. generated_reports
30. audit_logs
```

This inventory may be refined during implementation if a documented architectural reason exists.

---

# 80. Simplified ER Diagram

```text
┌──────────────────┐
│  organizations   │
└────────┬─────────┘
         │
   ┌─────┼────────────────────────────────────────────┐
   │     │                                            │
   ▼     ▼                                            ▼
 users  roads                                   audit_logs
   │     │
   │     ▼
   │  road_segments
   │     │
   │     ├──────────────┐
   │     ▼              ▼
   │ inspections   road_health_snapshots
   │     │
   │     ▼
   │ inspection_media
   │     │
   │     ▼
   │ processing_jobs
   │     │
   │     ▼
   │ ai_processing_runs
   │     │
   │     ▼
   │ ai_detections
   │     │
   │     ▼
   │ damage_records
   │     │
   │     ├──────────────► damage_reviews
   │     │
   │     ▼
   │ maintenance_damage_links
   │     │
   │     ▼
   │ maintenance_jobs
   │     │
   │     ├──────────────► maintenance_status_history
   │     │
   │     ▼
   │ repair_evidence
   │     │
   │     ▼
   │ repair_verifications
   │     │
   │     ▼
   │ recurrence_records
   │
   └──────────────► notifications
```

---

# 81. Initial Migration Order

Recommended migration sequence:

```text
001_extensions
002_organizations_users
003_roles_permissions
004_organization_memberships
005_roads
006_road_segments
007_inspections
008_inspection_media
009_processing_jobs
010_ai_models
011_ai_processing_runs
012_damage_types
013_ai_detections
014_damage_records
015_damage_reviews
016_road_health
017_maintenance_priority
018_predictions
019_maintenance_jobs
020_maintenance_damage_links
021_maintenance_status_history
022_repair_evidence
023_repair_verifications
024_recurrence
025_notifications
026_reports
027_audit_logs
028_optional_refresh_tokens
```

Actual Alembic revision identifiers will be generated by the migration system.

---

# 82. Initial Reference Data

The initial seed should contain:

## Roles

```text
ADMINISTRATOR
AUTHORITY
INSPECTOR
CONTRACTOR
```

## Damage Types

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

## Basic Permissions

Examples:

```text
dashboard.read

roads.read
roads.create
roads.update

inspections.read
inspections.create
inspections.update

damage.read
damage.review

maintenance.read
maintenance.create
maintenance.assign
maintenance.update

repair.submit
verification.read
verification.review

analytics.read
reports.generate

users.read
users.manage

audit.read
```

The complete permission matrix belongs in `USER_ROLES_PERMISSIONS.md`.

---

# 83. Schema Evolution

The schema must support future additions such as:

```text
Additional damage types
Additional AI models
Traffic data
Weather data
Citizen reports
Multiple municipalities
Advanced recurrence models
Advanced prediction models
GPU processing metadata
```

Future features should preferably extend the model rather than requiring destructive redesign.

---

# 84. Data Model Anti-Patterns

The following are prohibited:

### Anti-pattern 1

Store images directly in PostgreSQL bytea fields for normal application media.

### Anti-pattern 2

Store all application data in one JSONB table.

### Anti-pattern 3

Use email addresses as foreign keys.

### Anti-pattern 4

Use sequential public IDs for sensitive resources.

### Anti-pattern 5

Overwrite historical AI results.

### Anti-pattern 6

Delete damage history after repair.

### Anti-pattern 7

Store passwords directly.

### Anti-pattern 8

Allow organization IDs from clients to bypass authorization.

### Anti-pattern 9

Use Redis as permanent business storage.

### Anti-pattern 10

Store model outputs without model/version metadata.

### Anti-pattern 11

Store geographic coordinates without a documented spatial representation.

### Anti-pattern 12

Create unbounded database queries for dashboard collections.

---

# 85. Database Definition of Done

The database implementation is complete only when:

```text
[ ] PostgreSQL configured
[ ] PostGIS enabled
[ ] pgcrypto enabled
[ ] All core tables created
[ ] Foreign keys defined
[ ] Constraints defined
[ ] Indexes defined
[ ] Spatial indexes defined
[ ] Organization isolation implemented
[ ] AI model versioning implemented
[ ] Historical records preserved
[ ] Processing jobs implemented
[ ] Maintenance state history implemented
[ ] Repair verification persisted
[ ] Recurrence relationships persisted
[ ] Audit logging persisted
[ ] Alembic migrations created
[ ] Seed/reference data created
[ ] Database tests pass
[ ] Migration tested on clean database
[ ] No production secrets committed
```

---

# 86. Final Database Architecture

The authoritative database architecture is:

```text
                    PostgreSQL
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
    Identity           Roads          Inspections
       │                 │                 │
       │                 ▼                 ▼
       │           Road Segments         Media
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  AI Processing
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        AI Detections         AI Models/Runs
              │
              ▼
        Damage Records
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
   Health  Priority  Prediction
      │       │        │
      └───────┼────────┘
              ▼
        Maintenance
              │
              ▼
      Repair Evidence
              │
              ▼
      Repair Verification
              │
              ▼
          Recurrence
              │
              ▼
       Historical Data
```

Large files remain outside PostgreSQL:

```text
                    Supabase Storage
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       Inspection Media  Repair       Reports
                         Evidence
```

---

# 87. Final Database Principle

The database must preserve the complete chain:

```text
WHO
 ↓
captured WHAT
 ↓
WHERE
 ↓
WHEN
 ↓
AI analyzed it HOW
 ↓
WHAT model/version produced the result
 ↓
WHO reviewed it
 ↓
WHAT maintenance action occurred
 ↓
WHAT evidence was submitted
 ↓
HOW repair was verified
 ↓
WHETHER damage recurred
```

The database is therefore not merely a CRUD storage layer.

It is the **historical source of truth for the complete road-condition lifecycle**.

---

# 88. Coding-Agent Enforcement

Before modifying the database, the coding agent must:

1. Read `PROJECT_CONTEXT.md`.
2. Read `PRD.md`.
3. Read `SRS.md`.
4. Read `SYSTEM_ARCHITECTURE.md`.
5. Read `TECH_STACK.md`.
6. Read this database specification.
7. Identify the affected entities.
8. Preserve existing foreign-key relationships.
9. Preserve organization isolation.
10. Create an Alembic migration.
11. Update SQLAlchemy models.
12. Add/update database tests.
13. Add required indexes and constraints.
14. Verify migration on a clean database.
15. Avoid destructive changes unless explicitly approved.
16. Preserve historical AI and operational records.
17. Update dependent API specifications if schema changes affect API contracts.
18. Never expose database credentials to clients.

---

# 89. Source-of-Truth Rule

For database decisions:

```text
Approved Architecture
        ↓
DATABASE_SCHEMA.md
        ↓
Alembic Migrations
        ↓
SQLAlchemy Models
        ↓
Repositories
        ↓
Services
        ↓
API
```

The live database must not silently become a different architecture from the approved schema.

---

# 90. Final Statement

The database architecture establishes a normalized, organization-aware, geospatially capable, historically traceable foundation for:

```text
FIELD INSPECTION
      ↓
MEDIA
      ↓
AI DETECTION
      ↓
DAMAGE
      ↓
ROAD INTELLIGENCE
      ↓
PREDICTION
      ↓
MAINTENANCE
      ↓
REPAIR
      ↓
VERIFICATION
      ↓
RECURRENCE
      ↓
HISTORICAL ROAD INTELLIGENCE
```

Every subsequent backend, AI, Android, API, security, and analytics specification must remain compatible with this data model.

**End of `DATABASE_SCHEMA.md`**