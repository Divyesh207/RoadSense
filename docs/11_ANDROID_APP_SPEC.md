# ANDROID APP SPECIFICATION

**Project:** Road Intelligence & Pothole Management Platform  
**Document:** `ANDROID_APP_SPEC.md`  
**Version:** 1.0  
**Status:** Approved Specification  
**Primary Android User:** Field Inspector

---

## 1. Purpose

This document defines the complete functional, technical, architectural, UX, security, offline, synchronization, and testing requirements for the Android field application.

The Android application is the **field data collection client** for the Road Intelligence & Pothole Management Platform.

Its primary responsibility is to allow authorized field inspectors to:

- authenticate securely;
- select their organization and inspection context;
- capture road-condition media;
- capture accurate GPS information;
- associate observations with roads and road segments;
- create and manage inspections;
- operate when connectivity is unavailable;
- queue inspection data locally;
- synchronize data when connectivity returns;
- monitor upload and AI-processing status;
- review authorized inspection results;
- preserve field evidence and metadata.

The Android application is **not** the primary AI inference engine.

AI inference is performed by the backend AI worker using locally deployed models.

---

# 2. Source of Truth

The Android application must follow these documents:

1. `PROJECT_CONTEXT.md`
2. `PRD.md`
3. `SRS.md`
4. `SYSTEM_ARCHITECTURE.md`
5. `TECH_STACK.md`
6. `DATABASE_SCHEMA.md`
7. `API_SPECIFICATION.md`
8. `AI_ML_SPECIFICATION.md`
9. `USER_ROLES_PERMISSIONS.md`
10. `UI_UX_SPECIFICATION.md`
11. This document

If a conflict exists, the higher-level source-of-truth hierarchy defined in `PROJECT_CONTEXT.md` applies.

The Android application must not independently redefine backend contracts, database structures, AI behavior, or authorization rules.

---

# 3. Product Role

The Android application represents the **field execution layer** of the platform.

The canonical field workflow is:

```text
Inspector Login
      ↓
Organization Context
      ↓
Inspection Creation
      ↓
Road / Segment Selection
      ↓
GPS Acquisition
      ↓
Camera Capture
      ↓
Media Review
      ↓
Inspection Metadata
      ↓
Save Draft
      ↓
Submit
      ↓
Upload / Sync
      ↓
Backend Processing
      ↓
AI Analysis
      ↓
AI Results
      ↓
Human Review
      ↓
Maintenance Workflow
```

The Android application must preserve the complete chain between physical field observation and backend intelligence.

---

# 4. Primary User

## 4.1 Field Inspector

The primary Android user is the authorized:

```text
FIELD_INSPECTOR
```

The inspector can:

- log in;
- access authorized organizations;
- create inspections;
- capture road-condition evidence;
- capture GPS;
- select road/segment;
- submit inspections;
- view synchronization status;
- retry failed uploads;
- view authorized AI analysis;
- review inspection history;
- work offline.

The inspector must not receive administrative permissions merely because the Android application is installed.

---

# 5. Future Android Roles

The architecture should remain extensible for future mobile workflows.

Possible future roles may include:

- authorized maintenance personnel;
- contractor;
- supervisor;
- emergency inspection team.

However, these workflows are **not part of the initial Android MVP**.

The coding agent must not implement additional role-specific workflows unless explicitly requested.

---

# 6. Technology Stack

The approved Android stack is:

| Area | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose |
| Architecture | Presentation → Domain → Data |
| Camera | CameraX |
| Location | Android Location APIs / Fused Location Provider |
| Local DB | Room |
| Background Work | WorkManager |
| Networking | Retrofit + OkHttp |
| Serialization | Kotlinx Serialization |
| Authentication | JWT |
| Storage | Android secure storage mechanisms |
| Testing | JUnit + AndroidX Testing |
| Build | Gradle |
| Minimum architecture | Modular and testable |

The application must use modern Android APIs and avoid deprecated architecture patterns where practical.

---

# 7. Architecture

The Android application follows:

```text
Presentation
    ↓
Domain
    ↓
Data
```

Detailed structure:

```text
UI / Compose
    ↓
ViewModel
    ↓
Use Cases
    ↓
Repositories
    ↓
Remote Data Source / Local Data Source
    ↓
Retrofit / Room
```

The application must not allow UI components to directly access:

- Retrofit;
- Room;
- authentication tokens;
- backend implementation details;
- raw storage credentials.

---

# 8. Recommended Android Project Structure

```text
apps/android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/
│   │   │   │   └── .../
│   │   │   ├── res/
│   │   │   └── AndroidManifest.xml
│   │   └── test/
│   └── build.gradle.kts
│
├── core/
│   ├── common/
│   ├── network/
│   ├── database/
│   ├── security/
│   ├── location/
│   └── camera/
│
├── feature/
│   ├── auth/
│   ├── home/
│   ├── inspections/
│   ├── camera/
│   ├── sync/
│   └── profile/
│
├── domain/
│   ├── model/
│   ├── repository/
│   └── usecase/
│
└── build.gradle.kts
```

The exact package structure may evolve, but dependency direction must remain consistent.

---

# 9. Application Navigation

Initial navigation:

```text
Splash
  ↓
Authentication Check
  ├── Unauthenticated → Login
  └── Authenticated
          ↓
       Home
          ├── New Inspection
          ├── Inspections
          ├── Sync Queue
          └── Profile
```

Inspection navigation:

```text
Home
 ↓
New Inspection
 ↓
Road / Segment
 ↓
GPS
 ↓
Camera
 ↓
Media Review
 ↓
Inspection Details
 ↓
Save / Submit
 ↓
Sync Status
```

Inspection result navigation:

```text
Inspections
 ↓
Inspection Detail
 ↓
Processing Status
 ↓
AI Results
 ↓
Damage Details
```

---

# 10. Authentication

The application must use the backend authentication API.

Initial login:

```http
POST /api/v1/auth/login
```

The Android client receives an authenticated session according to the API contract.

The client must:

- securely store authentication material;
- attach access tokens to authorized requests;
- refresh tokens when supported;
- handle token expiration;
- clear local session data on logout;
- never log tokens.

---

# 11. Secure Token Storage

Authentication tokens must not be stored in:

- plain SharedPreferences;
- application logs;
- local database tables intended for business data;
- source code;
- hardcoded configuration.

Use an Android secure storage mechanism backed by platform security facilities.

The implementation should support:

```text
Access Token
Refresh Token
Session Metadata
```

with appropriate encryption/security controls.

---

# 12. Organization Context

The Android application operates within an organization context.

After authentication, the application must resolve the user's authorized organization membership.

The backend remains authoritative for authorization.

Where required by the API contract, requests must include:

```http
X-Organization-ID: <organization_uuid>
```

The client must never assume that a user can access an organization simply because an ID exists locally.

Every protected request must be authorized by the backend.

---

# 13. Permission Handling

The application may require:

- Camera permission
- Fine location permission
- Coarse location permission
- Notification permission where applicable
- Network access

Modern Android storage permissions should be avoided where unnecessary.

Captured media should use Android's application-scoped storage mechanisms and the platform media APIs.

---

# 14. Permission UX

Permissions must be requested contextually.

Example:

```text
User opens Camera
        ↓
Explain why camera access is required
        ↓
Request Camera Permission
        ↓
Granted → Continue
Denied → Explain limitation + retry option
```

Location:

```text
Inspection requires location
        ↓
Explain GPS requirement
        ↓
Request Location Permission
        ↓
Acquire Location
        ↓
Display accuracy
```

The application must not repeatedly request permissions without providing useful guidance.

---

# 15. Home Screen

The inspector home screen should provide:

### Summary

- active inspection;
- drafts;
- pending uploads;
- failed uploads;
- completed inspections;
- latest synchronization state.

### Primary actions

```text
+ New Inspection
View Inspections
Sync Queue
Profile
```

### Connectivity indicator

Display:

```text
ONLINE
OFFLINE
SYNCING
SYNC ERROR
```

The indicator must not be the only indication of sync state; individual records should also show their state.

---

# 16. Inspection Creation

Selecting **New Inspection** creates a client-side inspection identifier.

The ID should be generated before network submission.

Example:

```text
client_inspection_id = UUID
```

This enables offline creation and idempotent synchronization.

Initial state:

```text
LOCAL_DRAFT
```

The application should immediately persist the draft locally.

---

# 17. Inspection Metadata

An inspection may contain:

- client-generated inspection ID;
- road ID;
- road segment ID;
- inspector ID;
- organization ID;
- inspection timestamp;
- GPS latitude;
- GPS longitude;
- GPS accuracy;
- captured media;
- optional notes;
- optional field metadata;
- synchronization state.

Backend-generated fields must not be fabricated by the client.

---

# 18. Road Selection

The inspector should be able to select:

```text
Road
  ↓
Road Segment
```

The available roads and segments must be retrieved from the authorized backend context.

If offline, the application may use an appropriate cached dataset.

Offline cached data must clearly indicate that it may not represent the latest server state.

---

# 19. GPS Capture

GPS is a critical component of field inspection.

The application should capture:

- latitude;
- longitude;
- accuracy;
- timestamp;
- provider/source where available.

Example:

```json
{
  "latitude": 18.XXXX,
  "longitude": 73.XXXX,
  "accuracy_meters": 6.5,
  "captured_at": "UTC_TIMESTAMP"
}
```

The actual API payload must follow the backend contract.

---

# 20. GPS Accuracy

The application should display GPS accuracy to the inspector.

Example:

```text
GPS Accuracy: ±6 m
```

If accuracy is poor:

```text
GPS accuracy is low.
Move to an open area and try again.
```

The application must not silently present low-accuracy coordinates as highly precise.

---

# 21. GPS Association

The Android client may provide:

```text
latitude
longitude
```

The backend is responsible for authoritative road/segment association using PostGIS.

Therefore:

```text
Android GPS
      ↓
FastAPI
      ↓
PostGIS spatial matching
      ↓
Road Segment Association
```

The client must not permanently determine authoritative segment association using local geometry alone.

---

# 22. Camera

Camera functionality must use:

```text
CameraX
```

The camera workflow must support road-condition evidence capture.

Initial supported media:

- JPEG
- PNG
- MP4 where video capture is enabled.

The MVP should prioritize reliable image capture before advanced video functionality.

---

# 23. Camera Capture UX

Recommended flow:

```text
Camera Screen
 ├── Current GPS
 ├── Capture button
 ├── Flash control
 ├── Camera switch
 └── Exit
```

After capture:

```text
Captured Image
 ├── Retake
 ├── Keep
 └── Add Another
```

The application must avoid accidentally discarding captured evidence.

---

# 24. Capture Metadata

Each captured media item should retain:

- client media ID;
- inspection ID;
- local file reference;
- media type;
- capture timestamp;
- capture location;
- GPS accuracy;
- upload state;
- checksum/hash where implemented;
- retry count;
- server media ID after synchronization.

---

# 25. Media Validation

Before upload, the application should validate:

- file existence;
- supported MIME type;
- file size;
- readable media;
- non-empty content;
- local storage availability.

Invalid media must not enter the upload queue.

---

# 26. Media Compression

Media should be optimized before upload where appropriate.

For images:

- resize oversized images;
- preserve sufficient detail for AI inference;
- use controlled JPEG compression where applicable.

The application must not compress evidence to the point where potholes, cracks, or other damage become difficult for the AI model or human reviewer to identify.

Original-vs-processed evidence handling must follow the backend/storage policy.

---

# 27. Inspection Draft

The inspector must be able to save an incomplete inspection.

Example:

```text
LOCAL_DRAFT
```

A draft may contain:

- road;
- segment;
- GPS;
- notes;
- one or more media items.

The user may leave the application and return later.

---

# 28. Inspection State Machine

The Android application must represent the backend inspection lifecycle:

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

Local synchronization states:

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
UPLOAD_FAILED
    ↓
RETRY
```

The client must not invent incompatible states.

---

# 29. Offline-First Design

Offline operation is a core requirement.

The inspector may work in areas with:

- poor mobile connectivity;
- intermittent network;
- no network.

The application must allow field evidence collection without requiring continuous connectivity.

Core rule:

```text
No Network ≠ No Inspection
```

---

# 30. Local Persistence

Room should persist local operational data.

Potential local entities:

```text
LocalInspection
LocalInspectionMedia
LocalRoadCache
LocalSegmentCache
SyncQueueItem
SyncAttempt
LocalSessionMetadata
```

The local schema must not be treated as a replacement for the authoritative PostgreSQL schema.

Room is a client cache/work queue.

---

# 31. Local Inspection Entity

Conceptually:

```text
LocalInspection
----------------------------
id
server_id
client_id
organization_id
road_id
segment_id
inspector_id
status
latitude
longitude
accuracy
captured_at
notes
created_at
updated_at
sync_status
last_sync_error
```

The final Room schema should be implemented according to actual application needs.

---

# 32. Local Media Entity

Conceptually:

```text
LocalInspectionMedia
----------------------------
id
server_id
inspection_id
local_uri
media_type
file_size
checksum
captured_at
latitude
longitude
accuracy
upload_status
upload_attempts
last_error
created_at
updated_at
```

Local file references must not be confused with Supabase Storage object paths.

---

# 33. Sync Queue

The application must maintain a durable synchronization queue.

Example:

```text
SyncQueueItem
----------------------------
id
entity_type
entity_id
operation
priority
status
attempt_count
next_attempt_at
last_error
created_at
updated_at
```

Operations may include:

```text
CREATE_INSPECTION
UPLOAD_MEDIA
COMPLETE_MEDIA_UPLOAD
SUBMIT_INSPECTION
REQUEST_PROCESSING
```

Only operations supported by the API should be implemented.

---

# 34. WorkManager

WorkManager must handle durable background synchronization.

Example:

```text
Inspection saved
      ↓
SyncQueue
      ↓
WorkManager
      ↓
Network available?
      ├── No → Retry later
      └── Yes
           ↓
       Upload
           ↓
       Success / Failure
```

Recommended constraints:

```text
Network required for upload
```

Optional battery constraints may be applied to large operations.

---

# 35. Retry Strategy

Transient failures should use retry with backoff.

Example conceptual strategy:

```text
Attempt 1
   ↓
Failure
   ↓
Backoff
   ↓
Attempt 2
   ↓
Failure
   ↓
Backoff
   ↓
Attempt 3
```

Permanent failures must not be retried indefinitely.

The application should distinguish:

### Transient

- timeout;
- temporary server error;
- temporary network failure.

### Permanent / actionable

- unauthorized;
- invalid request;
- invalid media;
- resource no longer available.

---

# 36. Idempotency

Offline synchronization must prevent duplicate inspections.

Client-generated UUIDs and API idempotency mechanisms must be used according to `API_SPECIFICATION.md`.

Example:

```text
Client creates:

inspection_id = UUID-123
```

If upload occurs twice:

```text
Request 1 → accepted
Request 2 → recognized as duplicate
```

The backend remains authoritative.

---

# 37. Upload Flow

The preferred upload sequence is:

```text
Create Inspection
      ↓
Request Upload URL
      ↓
Upload Media
      ↓
Notify Backend Upload Complete
      ↓
Submit Inspection
      ↓
Request Processing
```

The exact implementation must follow the API contract.

The Android application must not upload media directly to PostgreSQL.

---

# 38. Object Storage

Inspection media is stored in object storage.

The Android application interacts with storage only through approved backend-issued mechanisms such as signed upload URLs.

The application must never contain:

- Supabase service-role keys;
- database passwords;
- storage admin credentials;
- AI model credentials.

---

# 39. Upload Progress

For large files, the UI should provide meaningful progress:

```text
Uploading
████████░░ 80%
```

For multiple files:

```text
3 / 5 files uploaded
```

The UI must not falsely report successful upload before the backend confirms the relevant operation.

---

# 40. AI Processing Status

After inspection submission, AI processing is asynchronous.

Expected sequence:

```text
SUBMITTED
    ↓
PROCESSING
    ↓
ANALYZED
```

The application should display:

```text
AI analysis in progress...
```

The application must not pretend that inference has completed locally.

---

# 41. AI Results

Where the user's permissions allow it, the Android application may display:

- detected damage type;
- confidence;
- severity;
- location;
- inspection association;
- processing status.

Example:

```text
Pothole
Confidence: 92%
Severity: HIGH
```

AI confidence must not be presented as a guarantee.

---

# 42. Human Review

AI results may require human review.

The Android application must clearly distinguish:

```text
AI DETECTION
```

from:

```text
HUMAN CONFIRMED
```

If an inspector is authorized to review results, their action must be sent to the backend and audited.

The original AI output must remain preserved.

---

# 43. Inspection Detail

Inspection detail should show:

### Header

- inspection ID;
- date/time;
- road;
- segment;
- status.

### Location

- latitude;
- longitude;
- accuracy;
- map preview where practical.

### Evidence

- captured images;
- media status.

### AI

- processing status;
- detections;
- severity.

### Synchronization

- uploaded;
- processing;
- failed;
- retry available.

---

# 44. Inspection History

The inspector should be able to view authorized inspections.

Filters may include:

- status;
- date;
- road;
- segment;
- synchronization state.

The API remains responsible for authoritative filtering and pagination.

---

# 45. Sync Queue Screen

The Sync Queue should show:

```text
Pending
Uploading
Completed
Failed
```

Example:

```text
Pending Uploads: 4

Inspection #A12
2 photos
Waiting for network

Inspection #A13
3 photos
Upload failed
[Retry]
```

The user should have enough information to understand why synchronization failed.

---

# 46. Manual Sync

The application may provide:

```text
Sync Now
```

This should trigger the existing synchronization mechanism rather than bypassing WorkManager architecture.

Manual synchronization must respect:

- authentication;
- network constraints;
- retry rules;
- idempotency;
- authorization.

---

# 47. Conflict Handling

Conflicts may occur when:

- cached road data becomes outdated;
- an inspection is modified elsewhere;
- server state changes while the device is offline.

General strategy:

```text
Server = authoritative
Local = pending/offline state
```

The application must never silently overwrite authoritative server data.

Conflicts should produce an explicit state or user-visible error when manual resolution is required.

---

# 48. Offline Road/Segment Cache

The application may cache frequently used road and segment information.

Cached records should contain freshness information.

Example:

```text
Last updated:
2 hours ago
```

If stale:

```text
Cached road information may be outdated.
```

The application must not present stale data as guaranteed current data.

---

# 49. Connectivity

Network state should be monitored through Android-compatible mechanisms.

The application should respond to:

```text
ONLINE
OFFLINE
METERED
UNAVAILABLE
```

The exact networking implementation must not assume continuous connectivity.

---

# 50. Error Handling

Errors must be understandable and actionable.

Examples:

### Authentication

```text
Your session has expired. Please sign in again.
```

### GPS

```text
Unable to obtain a reliable location.
Try moving to an open area.
```

### Upload

```text
Upload failed.
Your inspection is safely stored on this device.
It will retry automatically.
```

### Server

```text
The server could not process this request.
Please try again later.
```

Technical details may be logged securely but should not be exposed unnecessarily to users.

---

# 51. Offline Safety Principle

The application must never tell the inspector:

```text
Inspection saved successfully
```

if the inspection exists only temporarily in memory.

Instead:

```text
Saved on this device
Waiting for synchronization
```

must be used when appropriate.

---

# 52. Data Loss Prevention

Before deleting local inspection data, the application must verify that the relevant server-side operation has succeeded or the user explicitly confirms deletion.

The application must not automatically delete unsynchronized evidence.

---

# 53. Battery Management

Field applications can consume significant battery due to:

- camera;
- GPS;
- uploads;
- background work.

The implementation should:

- stop location updates when no longer needed;
- release camera resources appropriately;
- avoid continuous GPS tracking when unnecessary;
- use WorkManager for durable background work;
- avoid unnecessary polling;
- compress media efficiently;
- avoid repeated network requests.

---

# 54. Camera Resource Management

Camera resources must be released when:

- leaving the camera screen;
- application lifecycle changes;
- capture is completed;
- permission is revoked.

The application must not keep the camera active unnecessarily.

---

# 55. Location Resource Management

Location requests should be scoped to actual inspection requirements.

Recommended:

```text
Start location acquisition
        ↓
Acquire sufficiently accurate position
        ↓
Store location
        ↓
Stop unnecessary updates
```

Continuous tracking should only be introduced if explicitly required by a future inspection mode.

---

# 56. Security

The Android application must follow `SECURITY.md`.

Core requirements:

- secure authentication;
- encrypted token storage;
- HTTPS only in production;
- certificate/security configuration appropriate for production;
- no secrets in APK;
- no direct database access;
- no service-role credentials;
- signed storage URLs;
- minimum required permissions;
- secure logs;
- server-side authorization;
- secure local data handling.

---

# 57. Logging

Application logs must not contain:

- JWT tokens;
- passwords;
- sensitive credentials;
- signed storage URLs where avoidable;
- personal data unnecessarily;
- secret API keys.

Safe diagnostic fields may include:

```text
request_id
inspection_id
client_operation_id
sync_status
HTTP status
error code
```

Production logging must be appropriately restricted.

---

# 58. Request Correlation

Where supported, the application should send:

```http
X-Request-ID
```

or an equivalent client-generated correlation identifier.

This allows:

```text
Android
→ Nginx
→ FastAPI
→ Celery
→ AI Worker
```

to be correlated during troubleshooting.

---

# 59. API Client

Retrofit should expose typed interfaces for the backend API.

Conceptually:

```kotlin
interface InspectionApi {

    suspend fun createInspection(...)

    suspend fun getInspection(...)

    suspend fun submitInspection(...)

    suspend fun requestUploadUrl(...)

    suspend fun completeMediaUpload(...)

    suspend fun requestProcessing(...)
}
```

The actual method signatures must follow the final API contract.

---

# 60. Repository Pattern

The UI must interact through repositories/use cases.

Example:

```text
InspectionViewModel
        ↓
CreateInspectionUseCase
        ↓
InspectionRepository
        ↓
Room + Retrofit
```

Repositories coordinate local and remote sources.

---

# 61. Offline Repository Behavior

Conceptually:

```text
Create Inspection
      ↓
Write to Room
      ↓
Return success to UI
      ↓
Queue Sync
      ↓
WorkManager
      ↓
Remote API
```

This makes the field workflow resilient to network interruptions.

---

# 62. Domain Models

Domain models should be independent of:

- Retrofit DTOs;
- Room entities;
- Compose UI state.

Example conceptual separation:

```text
InspectionDto
InspectionEntity
Inspection
InspectionUiState
```

Mappings should be explicit.

---

# 63. UI State

Compose screens should use predictable state models.

Example:

```text
Loading
Content
Empty
Error
Offline
Syncing
```

Avoid scattered mutable state across composables.

ViewModels should own screen-level state.

---

# 64. Inspection UI State

Example:

```text
InspectionUiState
├── inspection
├── gpsState
├── cameraState
├── media
├── validationErrors
├── syncState
└── error
```

The actual implementation can evolve while maintaining clear state ownership.

---

# 65. Form Validation

Before submission, validate:

- required road/segment where applicable;
- GPS availability;
- required media;
- valid metadata;
- inspection state.

Validation should occur locally for UX and again on the backend for security and correctness.

---

# 66. Android and Backend Validation

Client validation is not security.

The backend must independently validate:

```text
Authentication
Authorization
Organization
Inspection
Media
Coordinates
State transition
Payload
```

The Android application must expect backend validation failures.

---

# 67. Notifications

Notifications may be used for meaningful events such as:

- upload failure;
- synchronization completed;
- processing completed;
- review required.

Notification behavior must respect Android notification permission requirements.

Notifications should not expose sensitive information unnecessarily.

---

# 68. Accessibility

The application should support:

- readable typography;
- sufficient touch target size;
- content descriptions;
- screen reader compatibility;
- meaningful focus order;
- non-color-only status indicators;
- clear error messages.

Color must never be the only way to communicate:

```text
severity
sync state
inspection state
error state
```

---

# 69. Localization

The initial application may use English.

Architecture should allow future localization.

User-visible strings should not be scattered as hardcoded text throughout business logic.

Use Android resource/string mechanisms.

---

# 70. Performance Requirements

The application should prioritize:

- fast launch;
- responsive Compose UI;
- low memory usage;
- efficient image handling;
- reliable background synchronization;
- minimal unnecessary network calls.

Large images should not be loaded into memory at full resolution when thumbnails are sufficient.

---

# 71. Large Media Handling

The application should avoid:

```text
Entire large media file
→ decode into RAM
```

when unnecessary.

Use:

- bounded decoding;
- thumbnails;
- streaming/file-based operations;
- appropriate compression.

The exact implementation depends on the media-processing library and API requirements.

---

# 72. Android Build Variants

Recommended variants:

```text
debug
staging
release
```

Each environment must use separate configuration.

Example:

```text
DEBUG_API_BASE_URL
STAGING_API_BASE_URL
PRODUCTION_API_BASE_URL
```

Secrets must not be committed to Git.

---

# 73. Environment Configuration

Production API URL must be configurable.

The application must not hardcode a developer's local IP address into production builds.

Local development may use:

```text
http://10.0.2.2:<PORT>
```

for Android Emulator access to a host machine where applicable.

---

# 74. Network Security

Production:

```text
HTTPS
```

HTTP should not be permitted for production API traffic.

If local HTTP is temporarily enabled for development, it must be isolated to the appropriate debug configuration.

---

# 75. Testing Strategy

Android testing must include:

### Unit Tests

- use cases;
- repositories;
- validation;
- state transitions;
- synchronization logic;
- retry logic;
- DTO/entity mapping.

### Instrumented Tests

- Room;
- WorkManager;
- authentication flow;
- inspection creation;
- offline persistence;
- permission behavior where practical.

### UI Tests

- login;
- home;
- inspection creation;
- camera workflow;
- offline inspection;
- sync queue;
- error states.

---

# 76. Offline Testing

At minimum test:

```text
Create inspection while offline
↓
Save locally
↓
Close app
↓
Reopen
↓
Inspection still exists
↓
Network restored
↓
Sync begins
↓
Server confirms
↓
Local state updates
```

Also test:

```text
Network fails during upload
↓
Upload marked failed
↓
Retry
↓
No duplicate inspection
```

---

# 77. GPS Testing

Test:

- accurate GPS;
- poor accuracy;
- no GPS;
- permission denied;
- location disabled;
- location changes during capture.

The application must behave explicitly in each case.

---

# 78. Camera Testing

Test:

- camera permission granted;
- camera permission denied;
- capture success;
- retake;
- multiple images;
- camera lifecycle;
- low storage;
- corrupted media;
- large media.

---

# 79. Synchronization Testing

Test:

- one pending inspection;
- multiple pending inspections;
- network loss;
- server timeout;
- unauthorized response;
- validation error;
- duplicate request;
- application restart during sync;
- WorkManager retry.

---

# 80. Security Testing

Verify:

- tokens are not logged;
- credentials are not stored in plain text;
- unauthorized API access is rejected;
- organization isolation is enforced server-side;
- no database credentials exist in APK;
- no Supabase service-role key exists in APK;
- production traffic uses HTTPS.

---

# 81. Observability

The application should expose enough structured diagnostics to troubleshoot:

```text
Authentication
Inspection creation
Media upload
Synchronization
API failures
WorkManager execution
AI processing status
```

Logs must remain privacy-conscious.

---

# 82. Analytics

Product analytics should not be introduced merely for tracking.

If analytics are implemented later, they must follow privacy requirements and must not interfere with field operations.

Operational logging and product analytics should remain conceptually separate.

---

# 83. Demo Mode

A demo mode may be supported if required by the overall product.

If implemented:

- demo data must be clearly marked;
- demo authentication must not bypass real authorization in production;
- demo data must not be mixed with real organization data;
- demo mode must not silently authenticate users into another account.

Demo behavior must be controlled through environment/feature configuration.

---

# 84. No Direct Database Access

The Android application must never connect directly to:

```text
PostgreSQL
Supabase PostgreSQL
```

All business operations go through:

```text
Android
→ HTTPS
→ FastAPI
```

This is a mandatory architectural constraint.

---

# 85. No AI API Credentials

The Android application must not contain:

```text
GEMINI_API_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
```

or equivalent AI-provider credentials.

AI inference occurs in the controlled backend AI worker.

---

# 86. No Fake AI Results

The Android application must never generate fabricated:

```text
damage detections
confidence values
severity values
prediction values
repair verification results
```

If backend AI processing has not completed, the application must display the actual processing state.

---

# 87. Field Evidence Integrity

The application must preserve the relationship:

```text
Inspector
↓
Inspection
↓
Media
↓
GPS
↓
Timestamp
↓
Road / Segment
```

Evidence metadata must not be silently replaced after synchronization.

---

# 88. Data Lifecycle

The Android data lifecycle is:

```text
Capture
 ↓
Local Persistence
 ↓
Validation
 ↓
Queue
 ↓
Upload
 ↓
Server Confirmation
 ↓
AI Processing
 ↓
Result Retrieval
 ↓
Local Cache
```

Local records may eventually be cleaned according to a defined retention policy, but unsynchronized evidence must never be deleted automatically.

---

# 89. API Versioning

The application must use:

```text
/api/v1/
```

and should not depend on undocumented endpoints.

API changes should be coordinated with the backend specification.

Breaking changes require:

- API versioning;
- coordinated Android update;
- migration strategy where required.

---

# 90. Backward Compatibility

The Android application should gracefully handle supported backend changes.

Examples:

```text
new optional field
new status
additional metadata
```

Unknown optional fields should not unnecessarily break parsing where the serialization strategy permits safe handling.

Breaking API changes must not be silently ignored.

---

# 91. App Update Strategy

Production releases should use versioned builds.

Before release:

```text
Build
↓
Unit Tests
↓
Instrumentation Tests
↓
UI Tests
↓
Security Checks
↓
Staging
↓
Field Validation
↓
Production
```

---

# 92. Failure Recovery

The application must recover from:

- process termination;
- device restart;
- network loss;
- WorkManager interruption;
- upload timeout;
- API failure;
- expired authentication;
- temporary storage failure.

Durable state must be stored in Room rather than only memory.

---

# 93. Critical Invariants

The Android implementation must preserve these invariants:

1. Unsynchronized evidence must not be silently deleted.
2. Client IDs must remain stable across retries.
3. Duplicate submissions must be prevented through idempotency.
4. Backend authorization is authoritative.
5. AI results are never fabricated.
6. GPS uncertainty must remain visible where relevant.
7. Original evidence must remain traceable.
8. The client never accesses PostgreSQL directly.
9. The client never contains server-side secrets.
10. Local state must survive application restarts when required.
11. Server state remains authoritative after synchronization.
12. State transitions must follow the defined lifecycle.
13. Failed uploads must be retryable where appropriate.
14. Permanent failures must not enter infinite retry loops.

---

# 94. Coding-Agent Rules

Any coding agent implementing the Android application must:

1. Read all approved project documents before implementation.
2. Treat this document as the Android-specific contract.
3. Never invent unsupported API endpoints.
4. Never invent database schemas inside the Android app.
5. Never add external AI APIs.
6. Never add direct database connectivity.
7. Never expose secrets.
8. Use Kotlin and Jetpack Compose.
9. Use Room for durable local state.
10. Use WorkManager for durable background synchronization.
11. Use CameraX for camera functionality.
12. Use Android location APIs for GPS.
13. Use Retrofit/OkHttp for API communication.
14. Preserve client-generated UUIDs.
15. Implement idempotent synchronization.
16. Preserve offline evidence.
17. Handle failures explicitly.
18. Do not fake successful uploads.
19. Do not fake AI results.
20. Do not silently swallow exceptions.
21. Do not bypass backend authorization.
22. Keep UI, domain, and data layers separated.
23. Add tests for important behavior.
24. Do not place secrets in Git.
25. Update documentation when architecture changes.

---

# 95. Android Definition of Done

An Android feature is complete only when:

- the UI exists;
- the required state is modeled;
- validation exists;
- API integration exists where required;
- local persistence exists where required;
- offline behavior is defined;
- synchronization behavior is defined;
- authorization is respected;
- error states exist;
- loading states exist;
- empty states exist;
- retry behavior exists where appropriate;
- logging is safe;
- tests exist;
- no secrets are committed;
- no fake functionality exists;
- the implementation matches the approved API and architecture.

---

# 96. MVP Android Scope

The initial Android MVP includes:

### Authentication

- Login
- Session handling
- Logout

### Field Inspection

- New inspection
- Road/segment selection
- GPS acquisition
- Camera capture
- Media preview
- Notes/metadata
- Draft saving

### Offline

- Room persistence
- Offline inspection creation
- Sync queue
- WorkManager synchronization
- Retry

### Backend Integration

- Inspection creation
- Media upload
- Inspection submission
- Processing request
- Inspection status
- AI result retrieval

### Inspector Experience

- Home
- Inspection history
- Inspection detail
- Sync queue
- Profile/logout

---

# 97. Explicitly Deferred Android Features

The following are not required for the initial Android MVP:

- advanced continuous road video analytics;
- real-time autonomous driving integration;
- on-device YOLO inference;
- advanced route optimization;
- contractor-specific workflow;
- citizen reporting;
- direct government API integration;
- advanced push notification infrastructure;
- advanced offline map tiles;
- AR road inspection;
- autonomous repair verification on-device.

These may be added later through controlled architecture changes.

---

# 98. Canonical Android Architecture

The final approved architecture is:

```text
┌─────────────────────────────────────────┐
│              Android App                │
│                                         │
│  Jetpack Compose                        │
│       ↓                                 │
│  ViewModels                             │
│       ↓                                 │
│  Domain Use Cases                       │
│       ↓                                 │
│  Repositories                           │
│      ↙       ↘                          │
│   Room       Retrofit / OkHttp          │
│      ↓             ↓                    │
│ Local State      FastAPI                │
│                     ↓                   │
│                 PostgreSQL              │
│                     +                   │
│                Object Storage           │
│                     ↓                   │
│                  AI Worker              │
└─────────────────────────────────────────┘
```

---

# 99. Canonical Field Data Flow

```text
FIELD INSPECTOR
      ↓
ANDROID APP
      ↓
CAMERA + GPS
      ↓
LOCAL ROOM
      ↓
SYNC QUEUE
      ↓
WORKMANAGER
      ↓
FASTAPI
      ↓
AUTHENTICATION + AUTHORIZATION
      ↓
INSPECTION RECORD
      ↓
OBJECT STORAGE
      ↓
AI PROCESSING JOB
      ↓
CELERY / AI WORKER
      ↓
YOLO + OpenCV
      ↓
DAMAGE CLASSIFICATION
      ↓
SEVERITY ASSESSMENT
      ↓
POSTGRESQL / POSTGIS
      ↓
ANDROID / WEB REVIEW
      ↓
MAINTENANCE
      ↓
REPAIR
      ↓
VERIFICATION
      ↓
RECURRENCE / HISTORICAL INTELLIGENCE
```

---

# 100. Final Android Principle

The Android application is the **trusted field evidence collection and synchronization layer** of the Road Intelligence Platform.

Its job is not to replace the backend.

Its job is to reliably capture:

```text
WHO
+
WHAT
+
WHERE
+
WHEN
+
EVIDENCE
```

and transfer that information safely into the central intelligence pipeline:

```text
FIELD OBSERVATION
→ AI ANALYSIS
→ HUMAN REVIEW
→ ROAD INTELLIGENCE
→ MAINTENANCE
→ REPAIR
→ VERIFICATION
→ RECURRENCE
→ HISTORICAL LEARNING
```

The Android application must therefore prioritize:

**reliable field capture, offline resilience, evidence integrity, secure synchronization, explicit state management, and faithful interaction with the backend contracts.**

It must never sacrifice data integrity for superficial UI behavior or simulated functionality.