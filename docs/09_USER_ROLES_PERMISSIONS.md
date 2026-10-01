# USER ROLES & PERMISSIONS

**Project:** Road Intelligence & Pothole Management Platform  
**Document:** 09 — User Roles & Permissions  
**Status:** Approved Specification  
**Version:** 1.0  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`, `SRS.md`, `SYSTEM_ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `AI_ML_SPECIFICATION.md`

---

## 1. Purpose

This document defines the authorization model for the Road Intelligence & Pothole Management Platform.

It specifies:

- User roles
- System actors
- Permissions
- Organization isolation
- Resource-level authorization
- Role assignment
- Authentication context
- API authorization
- Web route protection
- Android authorization behavior
- State-transition permissions
- Audit requirements
- Access lifecycle
- RBAC testing requirements

This document is the source of truth for implementing authorization across the web application, Android application, FastAPI backend, background workers, and AI workers.

---

# 2. Authorization Principles

The authorization system MUST follow these principles:

1. **Deny by default**
2. **Least privilege**
3. **Organization isolation**
4. **Server-side authorization**
5. **Resource-level authorization**
6. **Explicit state-transition authorization**
7. **Audit sensitive actions**
8. **No client-side permission enforcement as the only security layer**
9. **System actors use controlled service permissions**
10. **Historical records must remain protected from unauthorized modification**
11. **Authentication and authorization are separate concerns**
12. **Every protected API operation must pass authorization checks**

The frontend or Android application may hide unavailable actions for usability, but the backend MUST independently enforce all authorization rules.

---

# 3. Multi-Tenant Organization Model

The platform is organization-aware.

An organization represents an authority, municipality, road-management department, contractor organization, or other approved operational entity.

Core relationship:

```text
Organization
    │
    ├── Users
    │     └── Organization Membership
    │            └── Role
    │
    ├── Roads
    ├── Road Segments
    ├── Inspections
    ├── Damages
    ├── Maintenance Jobs
    ├── Repair Evidence
    ├── Predictions
    ├── Reports
    └── Audit Logs
```

A user MAY belong to multiple organizations.

A user's permissions are resolved from their membership in the currently active organization.

---

# 4. User Roles

The platform defines four interactive user roles.

## 4.1 Administrator

The Administrator manages organization-level platform configuration and access.

Responsibilities include:

- Managing organization membership
- Assigning roles
- Activating/deactivating memberships
- Managing permissions through approved role configuration
- Managing organization-level settings
- Reviewing audit logs
- Managing operational configuration
- Accessing system-wide organization data where authorized

The Administrator MUST NOT automatically bypass all application rules simply because of the role.

Sensitive operations remain subject to authorization, state validation, and audit logging.

---

## 4.2 Road Authority / Municipal Official

The Road Authority / Municipal Official manages road intelligence and operational decisions.

Responsibilities include:

- Viewing roads and road segments
- Reviewing inspections
- Reviewing AI detections
- Confirming or rejecting damage
- Reviewing road health
- Reviewing deterioration predictions
- Creating maintenance jobs
- Assigning maintenance work
- Monitoring maintenance progress
- Reviewing repair verification
- Viewing analytics
- Generating reports
- Monitoring recurrence

This role represents the primary operational authority for road-management decisions.

---

## 4.3 Field Inspector

The Field Inspector collects road-condition information from the Android application.

Responsibilities include:

- Creating inspections
- Capturing road media
- Capturing GPS information
- Submitting inspections
- Uploading inspection media
- Viewing assigned inspection work
- Reviewing their submitted inspections where permitted
- Providing inspection observations
- Retrying failed uploads
- Operating in offline mode

The Field Inspector MUST NOT directly modify authoritative maintenance records unless explicitly granted an additional permission in a future approved configuration.

---

## 4.4 Maintenance / Contractor

The Maintenance / Contractor role is responsible for executing assigned maintenance work.

Responsibilities include:

- Viewing assigned maintenance jobs
- Updating permitted maintenance statuses
- Viewing linked damage
- Uploading repair evidence
- Completing assigned maintenance work
- Viewing repair-verification results where permitted
- Responding to rejected verification

A contractor MUST only access maintenance information authorized for their organization and assigned work.

---

# 5. System Actors

Two non-interactive system actors are defined.

## 5.1 AI Worker

The AI Worker performs automated processing.

Responsibilities include:

- Processing inspection media
- Running YOLO inference
- Running preprocessing/postprocessing
- Creating raw AI detections
- Calculating AI-derived attributes
- Running severity assessment
- Creating road-health inputs
- Running deterioration predictions
- Processing repair-verification evidence
- Recording model/version metadata
- Updating asynchronous processing jobs

The AI Worker MUST NOT:

- Approve its own AI output as human-reviewed
- Change human review decisions
- Assign maintenance jobs
- Bypass audit requirements
- Delete historical AI results

---

## 5.2 Background Worker

The Background Worker handles asynchronous platform operations.

Responsibilities may include:

- Processing queued jobs
- Generating reports
- Sending notifications
- Performing scheduled calculations
- Running maintenance/cleanup operations
- Executing approved asynchronous workflows

Background Worker operations MUST use explicit service permissions and MUST be auditable where they modify important records.

---

# 6. Permission Naming Convention

Permissions use the following format:

```text
<resource>:<action>
```

Examples:

```text
roads:read
roads:create
roads:update

inspections:create
inspections:submit

damages:read
damages:review

maintenance:create
maintenance:assign
maintenance:update
```

Permission names MUST be:

- Lowercase
- Resource-oriented
- Action-oriented
- Stable
- Explicit
- Reusable across clients

The backend MUST NOT rely on role-name strings as the only authorization mechanism.

---

# 7. Permission Catalog

## 7.1 Organization & User Permissions

```text
organizations:read
organizations:update
organizations:manage

users:read
users:manage

memberships:read
memberships:manage

roles:read
roles:manage
```

---

## 7.2 Road Permissions

```text
roads:read
roads:create
roads:update
roads:delete

road_segments:read
road_segments:create
road_segments:update
road_segments:delete
```

Deletion MUST be restricted because road and segment records may be referenced by historical inspections, damages, predictions, and maintenance records.

Where historical integrity requires it, deactivation/archiving SHOULD be preferred over physical deletion.

---

## 7.3 Inspection Permissions

```text
inspections:read
inspections:create
inspections:update
inspections:submit
inspections:process
inspections:review
```

Media permissions:

```text
inspection_media:read
inspection_media:upload
inspection_media:delete
```

Media deletion MUST respect historical and audit requirements.

---

## 7.4 AI & Damage Permissions

```text
ai_runs:read
ai_runs:process

damages:read
damages:create
damages:update
damages:review
damages:resolve

damage_types:read
damage_types:manage
```

Raw AI detections and canonical damage records MUST remain distinguishable.

Human review permissions apply to canonical review workflows and MUST NOT rewrite the original raw AI output.

---

## 7.5 GIS Permissions

GIS access follows the underlying resource permissions.

Additional map permissions MAY include:

```text
map:read
map:export
```

A user with `map:read` MUST still only receive geographically authorized resources.

---

## 7.6 Road Health Permissions

```text
road_health:read
road_health:calculate
```

Historical road-health snapshots MUST NOT be silently overwritten.

---

## 7.7 Prediction Permissions

```text
predictions:read
predictions:create
predictions:manage
```

Prediction access MUST preserve:

- Model version
- Feature version
- Prediction timestamp
- Input snapshot
- Prediction horizon
- Prediction value
- Uncertainty/confidence where supported

Predictions are decision-support information and MUST NOT be treated as guaranteed future outcomes.

---

## 7.8 Maintenance Permissions

```text
maintenance:read
maintenance:create
maintenance:update
maintenance:assign
maintenance:status_update
maintenance:link_damage
maintenance:view_history
```

Maintenance assignment and status changes MUST be independently authorized.

---

## 7.9 Repair Evidence Permissions

```text
repair_evidence:read
repair_evidence:upload
repair_evidence:delete
```

Repair evidence MUST remain associated with the relevant maintenance job.

---

## 7.10 Repair Verification Permissions

```text
repair_verifications:read
repair_verifications:create
repair_verifications:review
```

AI-generated verification results MUST NOT automatically become human-approved verification decisions.

---

## 7.11 Recurrence Permissions

```text
recurrence:read
recurrence:create
recurrence:review
```

Recurrence records MUST preserve links to historical damage, maintenance, repair, and verification records.

---

## 7.12 Analytics Permissions

```text
analytics:read
analytics:export

reports:read
reports:generate
reports:download
```

Generated reports MUST respect the requesting user's organization and resource permissions.

---

## 7.13 Notification Permissions

```text
notifications:read
notifications:manage
```

Users may read their authorized notifications.

System-generated notifications MUST be produced by authorized backend workflows.

---

## 7.14 Audit Permissions

```text
audit_logs:read
audit_logs:export
```

Audit logs MUST be protected from unauthorized modification.

Normal users MUST NOT modify or delete audit records.

---

# 8. Role-Permission Matrix

The following matrix defines the baseline authorization model.

| Permission Area | Administrator | Authority | Inspector | Contractor |
|---|---:|---:|---:|---:|
| Organization management | ✓ | — | — | — |
| User/member management | ✓ | — | — | — |
| Road read | ✓ | ✓ | ✓ | Assigned/authorized |
| Road create/update | ✓ | ✓ | — | — |
| Road segment management | ✓ | ✓ | — | — |
| Inspection create | ✓ | ✓ | ✓ | — |
| Inspection submit | ✓ | ✓ | ✓ | — |
| Inspection review | ✓ | ✓ | — | — |
| Inspection processing | ✓ | ✓ | — | — |
| Inspection media upload | ✓ | ✓ | ✓ | — |
| AI result read | ✓ | ✓ | ✓* | ✓* |
| Damage review | ✓ | ✓ | — | — |
| Road health read | ✓ | ✓ | Authorized | Authorized |
| Prediction read | ✓ | ✓ | Authorized | Authorized |
| Prediction management | ✓ | ✓ | — | — |
| Maintenance create | ✓ | ✓ | — | — |
| Maintenance assign | ✓ | ✓ | — | — |
| Maintenance update | ✓ | ✓ | — | Assigned jobs |
| Repair evidence upload | ✓ | ✓ | — | ✓ |
| Repair verification review | ✓ | ✓ | — | — |
| Recurrence review | ✓ | ✓ | — | — |
| Analytics read | ✓ | ✓ | Limited/authorized | Limited/authorized |
| Report generation | ✓ | ✓ | —/authorized | —/authorized |
| Audit log read | ✓ | Authorized | — | — |

`*` Access is limited to resources and information explicitly permitted by the deployment's privacy and operational rules.

The matrix is a baseline. The backend MUST enforce explicit permissions and resource-level authorization rather than relying solely on this table.

---

# 9. Resource-Level Authorization

Role permission alone is insufficient.

A request MUST also pass resource-level authorization.

Example:

```text
User has:
maintenance:read
```

This does NOT automatically mean:

```text
User can read every maintenance job in the system.
```

The backend MUST verify:

1. User is authenticated.
2. User has an active organization membership.
3. User has the required permission.
4. Requested resource belongs to the active organization.
5. User has access to that resource according to operational rules.
6. Requested state transition is permitted.

---

# 10. Organization Isolation

Every organization-scoped resource MUST be associated with an organization.

Examples:

```text
roads.organization_id
inspections.organization_id
maintenance_jobs.organization_id
audit_logs.organization_id
```

The backend MUST prevent cross-organization access.

A request such as:

```text
GET /api/v1/maintenance/{id}
```

MUST verify that the requested maintenance record belongs to an organization the authenticated user is authorized to access.

The organization ID supplied by the client MUST NOT be treated as proof of authorization.

---

# 11. `X-Organization-ID`

The API supports organization context through:

```http
X-Organization-ID: <organization_uuid>
```

The backend MUST:

1. Authenticate the JWT.
2. Resolve the user.
3. Resolve the requested organization.
4. Verify active membership.
5. Resolve the user's role and permissions for that organization.
6. Establish organization context.
7. Continue authorization.

If the header references an organization where the user has no active membership, the request MUST be rejected.

The server MUST NOT allow users to switch organizations merely by changing the header.

---

# 12. JWT Claims

The access token MAY contain claims such as:

```json
{
  "sub": "user_uuid",
  "type": "access",
  "jti": "token_uuid",
  "iat": 0,
  "exp": 0
}
```

Organization membership and permission information SHOULD be resolved server-side when appropriate rather than placing large mutable permission sets permanently inside tokens.

If role or permission information is included in a token, token expiration and membership changes MUST be handled safely.

JWTs MUST NOT contain:

- Passwords
- Secrets
- API keys
- Database credentials
- Private storage credentials
- Sensitive raw media

---

# 13. Authentication vs Authorization

Authentication answers:

> Who is the user?

Authorization answers:

> What is this authenticated user allowed to do?

The request flow is:

```text
Request
→ Authenticate
→ Resolve User
→ Resolve Organization Membership
→ Resolve Role
→ Check Permission
→ Check Resource Ownership/Org
→ Check State Transition
→ Allow / Deny
→ Audit Sensitive Action
```

Authentication MUST occur before authorization.

Authorization MUST occur before protected business logic executes.

---

# 14. API Authorization Flow

FastAPI endpoints MUST use centralized authorization dependencies/services.

Conceptually:

```text
HTTP Request
    ↓
JWT Authentication
    ↓
User Resolution
    ↓
Organization Context
    ↓
Membership Validation
    ↓
Permission Check
    ↓
Resource Authorization
    ↓
State Transition Validation
    ↓
Application Service
    ↓
Repository
    ↓
Database
```

Authorization logic MUST NOT be duplicated independently across dozens of endpoints.

Reusable authorization components SHOULD be provided for:

```text
require_authenticated_user()
require_organization_membership()
require_permission()
require_resource_access()
require_state_transition()
```

---

# 15. State-Transition Authorization

Authorization MUST consider the current state of a resource.

## 15.1 Inspection

Canonical flow:

```text
DRAFT
→ SUBMITTED
→ UPLOADING
→ PROCESSING
→ ANALYZED
→ REVIEW_REQUIRED
→ REVIEWED
→ COMPLETED
```

A user must have both:

1. Permission to perform the action.
2. Authority to perform the requested transition.

For example:

```text
inspections:submit
```

does not permit:

```text
COMPLETED → DRAFT
```

unless such a transition is explicitly defined and authorized.

---

## 15.2 Maintenance

Canonical flow:

```text
OPEN
→ ASSIGNED
→ IN_PROGRESS
→ COMPLETED
→ VERIFICATION_PENDING
→ VERIFIED
```

Alternative transitions:

```text
IN_PROGRESS → CANCELLED

VERIFICATION_PENDING → REJECTED

REJECTED → IN_PROGRESS
```

A contractor may update an assigned maintenance job where authorized, but MUST NOT automatically mark the job as human-verified.

---

# 16. Administrator Authorization

Administrators have broad organization-management capabilities but MUST still follow:

- Organization boundaries
- Resource validation
- State-transition rules
- Audit requirements
- Data integrity rules
- Security controls

Administrator access MUST NOT be implemented as:

```python
if user.role == "admin":
    allow_everything()
```

Instead, permissions and resource authorization MUST remain explicit.

---

# 17. Field Inspector Authorization

The Android application MUST expose only actions available to the authenticated inspector.

Typical inspector flow:

```text
Login
→ Resolve Organization
→ Load Authorized Work
→ Create Inspection
→ Capture Media
→ Capture GPS
→ Save Offline if Needed
→ Upload
→ Submit
→ Track Processing
```

The inspector MUST NOT be able to:

- Change another organization's data
- Modify raw AI output
- Approve their own AI analysis as independent review
- Assign maintenance jobs unless explicitly authorized
- Modify audit logs

---

# 18. Contractor Authorization

Contractor access MUST be restricted to authorized maintenance work.

A contractor may typically:

```text
View assigned maintenance
        ↓
View linked damage
        ↓
Update permitted status
        ↓
Upload repair evidence
        ↓
Complete maintenance
        ↓
Wait for verification
```

Contractors MUST NOT:

- Modify original AI detections
- Approve their own repair verification
- Modify road-health calculations
- Modify predictions
- Access unrelated organization data

---

# 19. AI Worker Authorization

The AI Worker is a system actor.

It requires controlled service credentials or another secure service-authentication mechanism.

It may:

```text
Read authorized media
→ Process media
→ Create AI processing run
→ Create raw detections
→ Create derived AI outputs
→ Store model/version metadata
→ Update processing job
```

It MUST NOT:

```text
Create human review decisions
Assign maintenance
Override reviewers
Delete historical records
```

All AI results MUST identify the relevant model/version.

---

# 20. Background Worker Authorization

The Background Worker performs controlled asynchronous tasks.

Examples:

```text
Report Generation
Notification Delivery
Scheduled Analytics
Prediction Jobs
Maintenance Tasks
Cleanup Operations
```

Worker actions MUST be scoped to the job and organization context being processed.

A background worker MUST NOT receive unrestricted database access merely because it is an internal service.

---

# 21. Frontend Route Guards

The web application SHOULD implement route-level and component-level permission checks.

Example:

```text
/dashboard
/roads
/inspections
/damages
/map
/maintenance
/analytics
/reports
/admin
```

Frontend guards improve usability but are NOT security boundaries.

The API remains authoritative.

Example:

```text
Frontend:
User lacks maintenance:create
→ Hide "Create Maintenance Job"

Backend:
POST /maintenance
→ Check maintenance:create
→ Reject if missing
```

---

# 22. Android Authorization Behavior

The Android application MUST:

- Authenticate securely.
- Store tokens using appropriate secure Android mechanisms.
- Resolve organization context.
- Respect server-provided authorization.
- Hide unavailable actions.
- Prevent unauthorized local workflows where possible.
- Still rely on backend authorization.
- Queue authorized offline operations.
- Revalidate authorization when synchronizing where required.

Offline mode MUST NOT become an authorization bypass.

If a user's membership is revoked while an operation is queued offline, the backend MUST reject unauthorized synchronization.

---

# 23. Membership States

Organization memberships SHOULD support explicit lifecycle states.

Recommended states:

```text
INVITED
ACTIVE
SUSPENDED
DEACTIVATED
```

Only `ACTIVE` memberships should normally authorize operational access.

### INVITED

The user has been invited but has not completed activation.

### ACTIVE

The user can authenticate and operate according to assigned permissions.

### SUSPENDED

Access is temporarily disabled.

### DEACTIVATED

The membership is no longer active.

Historical records created by a deactivated user MUST remain attributable to that user.

---

# 24. Role Assignment Lifecycle

Role changes MUST be controlled.

Typical flow:

```text
Administrator
    ↓
Select Organization Member
    ↓
Assign / Change Role
    ↓
Validate Permission
    ↓
Persist Membership Change
    ↓
Audit Change
```

Role changes SHOULD take effect promptly.

Previously issued tokens MUST NOT allow indefinite access after critical authorization changes.

---

# 25. Sensitive Actions

The following actions SHOULD require explicit confirmation and MUST be audited:

- Creating or modifying organization configuration
- Adding/removing organization members
- Changing roles
- Deactivating users
- Deleting or archiving important resources
- Assigning maintenance
- Changing maintenance state
- Approving damage reviews
- Approving repair verification
- Generating sensitive reports
- Exporting sensitive data
- Changing AI/model configuration

Where appropriate, re-authentication or elevated confirmation MAY be required.

---

# 26. Audit Logging

Authorization-sensitive actions MUST generate audit records.

Audit records SHOULD include:

```text
actor_id
organization_id
action
resource_type
resource_id
timestamp
request_id
result
metadata
```

Example:

```text
Actor:
User UUID

Action:
maintenance.assign

Resource:
Maintenance Job UUID

Result:
SUCCESS

Timestamp:
UTC timestamp

Request ID:
Request UUID
```

Authorization failures MAY also be logged where appropriate without exposing sensitive information.

---

# 27. Error Handling

## 27.1 Unauthenticated

Return:

```http
401 Unauthorized
```

Example:

```json
{
  "error": {
    "code": "UNAUTHENTICATED",
    "message": "Authentication is required.",
    "details": {},
    "request_id": "..."
  }
}
```

---

## 27.2 Unauthorized

Return:

```http
403 Forbidden
```

Example:

```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You do not have permission to perform this action.",
    "details": {},
    "request_id": "..."
  }
}
```

The API SHOULD avoid revealing unnecessary information about protected resources.

---

## 27.3 Organization Access Failure

When the user is not authorized for the requested organization, the backend MUST reject the request.

The response MUST NOT reveal protected organization information.

---

# 28. Permission Checks and Business Logic

Authorization MUST happen before business logic performs protected mutations.

Incorrect:

```text
Endpoint
→ Modify database
→ Check permission
```

Correct:

```text
Endpoint
→ Authenticate
→ Authorize
→ Validate request
→ Execute business logic
→ Persist
→ Audit
```

For complex workflows:

```text
Permission Check
+
Resource Check
+
State Check
+
Business Validation
```

All four may be required.

---

# 29. Data Access Rules

Database queries MUST be organization-aware.

Repositories SHOULD require organization context where appropriate.

Example conceptual query:

```text
Get maintenance job
WHERE id = requested_id
AND organization_id = current_organization_id
```

The backend MUST avoid patterns where a resource is loaded globally and authorization is checked only later.

Prefer scoped queries whenever possible.

---

# 30. API Permission Mapping

Representative endpoint authorization:

| Endpoint | Required Permission |
|---|---|
| `GET /roads` | `roads:read` |
| `POST /roads` | `roads:create` |
| `PATCH /roads/{id}` | `roads:update` |
| `POST /inspections` | `inspections:create` |
| `POST /inspections/{id}/submit` | `inspections:submit` |
| `GET /damages` | `damages:read` |
| `POST /damages/{id}/review` | `damages:review` |
| `POST /maintenance` | `maintenance:create` |
| `POST /maintenance/{id}/assign` | `maintenance:assign` |
| `PATCH /maintenance/{id}` | `maintenance:update` |
| `POST /maintenance/{id}/repair-evidence` | `repair_evidence:upload` |
| `POST /repair-verifications/{id}/review` | `repair_verifications:review` |
| `GET /analytics/dashboard` | `analytics:read` |
| `POST /reports` | `reports:generate` |
| `GET /audit-logs` | `audit_logs:read` |

This table is representative; implementation MUST remain aligned with `API_SPECIFICATION.md`.

---

# 31. Permission Management

The initial system uses predefined permissions.

Permissions MUST NOT be dynamically created by arbitrary users.

Any future custom-role functionality MUST:

1. Use predefined permissions.
2. Validate permission combinations.
3. Prevent privilege escalation.
4. Preserve organization boundaries.
5. Audit role changes.
6. Prevent users from granting permissions they themselves do not control.

---

# 32. Least Privilege

Every role MUST receive only the permissions required for its operational responsibilities.

Examples:

```text
Inspector
→ Inspection collection
→ Inspection submission
→ Authorized inspection visibility
```

```text
Contractor
→ Assigned maintenance
→ Repair evidence
→ Permitted status updates
```

```text
Authority
→ Operational road intelligence
→ Damage review
→ Maintenance management
→ Analytics
```

```text
Administrator
→ Organization and access management
```

The permission model MUST avoid granting broad database or infrastructure privileges to application users.

---

# 33. Service-to-Service Security

Internal services such as:

```text
FastAPI
Celery Worker
AI Worker
Redis
```

MUST use controlled credentials and network restrictions.

The AI Worker MUST NOT expose unrestricted administrative endpoints.

Redis MUST NOT be publicly exposed.

Database credentials MUST remain server-side.

Supabase service-role credentials MUST never be embedded in:

- Web client JavaScript
- Android APK
- Public source code
- Client-side environment variables

---

# 34. Testing Strategy for RBAC

RBAC MUST be tested at multiple levels.

## Unit Tests

Test:

- Permission evaluation
- Role mapping
- Membership state
- Organization resolution
- State-transition authorization

Example:

```text
ACTIVE Inspector
+ inspections:create
→ ALLOW inspection creation
```

```text
DEACTIVATED Inspector
+ inspections:create
→ DENY
```

---

## API Tests

Test:

- Missing authentication
- Invalid token
- Expired token
- Missing permission
- Wrong organization
- Wrong resource
- Invalid state transition
- Authorized operation
- Audit creation

---

## Cross-Organization Tests

Explicitly test:

```text
Organization A user
→ Organization B road
→ DENY
```

```text
Organization A user
→ Organization A road
→ ALLOW if permission exists
```

---

## Role Escalation Tests

Test that:

```text
Inspector
→ Cannot assign themselves Administrator
```

```text
Contractor
→ Cannot approve their own repair verification
```

```text
AI Worker
→ Cannot create human review decision
```

---

# 35. Security Requirements

The authorization implementation MUST ensure:

- Passwords are never stored in plaintext.
- Password verification uses bcrypt or approved secure password hashing.
- JWT signing keys remain server-side.
- Refresh-token handling follows secure lifecycle rules if enabled.
- HTTPS is required outside local development.
- CORS is explicitly configured.
- Rate limiting protects authentication endpoints.
- Authorization is enforced server-side.
- Sensitive operations are audited.
- Secrets are stored in environment/secret management systems.
- Client applications never receive database credentials.
- Organization isolation is enforced at the API/data layer.

---

# 36. Coding-Agent Implementation Rules

Coding agents implementing authorization MUST follow these rules.

### Rule 1 — Read the Documentation First

Before modifying authorization code, read:

```text
PROJECT_CONTEXT.md
PRD.md
SRS.md
SYSTEM_ARCHITECTURE.md
DATABASE_SCHEMA.md
API_SPECIFICATION.md
USER_ROLES_PERMISSIONS.md
```

### Rule 2 — Do Not Invent Roles

Do not create additional interactive roles without an approved architecture change.

### Rule 3 — Do Not Trust the Client

Never treat frontend or Android permission state as authoritative.

### Rule 4 — Enforce Organization Isolation

Every organization-scoped resource access must be authorized.

### Rule 5 — Do Not Bypass State Machines

Authorization does not permit invalid state transitions.

### Rule 6 — Preserve Auditability

Sensitive authorization changes must be auditable.

### Rule 7 — Do Not Hardcode Secrets

Never commit JWT keys, passwords, API keys, or database credentials.

### Rule 8 — Reuse Authorization Components

Avoid duplicated authorization logic across endpoints.

### Rule 9 — Test Negative Cases

Every protected operation must include unauthorized and cross-organization tests.

### Rule 10 — Preserve Existing Contracts

Authorization changes MUST NOT silently break API contracts, database invariants, or client synchronization.

---

# 37. Definition of Done

An authorization feature is complete only when:

- [ ] Authentication is implemented.
- [ ] Organization context is resolved.
- [ ] Membership state is validated.
- [ ] Role is resolved.
- [ ] Required permission is checked.
- [ ] Resource-level authorization is checked.
- [ ] State transition is validated where applicable.
- [ ] Cross-organization access is prevented.
- [ ] Sensitive actions are audited.
- [ ] Unauthorized requests return correct errors.
- [ ] Frontend guards are implemented where appropriate.
- [ ] Android behavior respects authorization.
- [ ] API tests exist.
- [ ] Negative authorization tests exist.
- [ ] Cross-tenant tests exist.
- [ ] No secrets are exposed.
- [ ] Documentation is updated.
- [ ] Existing contracts remain compatible.

---

# 38. Authorization Acceptance Checklist

Before release:

### Authentication

- [ ] Login requires valid credentials.
- [ ] Expired tokens are rejected.
- [ ] Invalid tokens are rejected.
- [ ] Deactivated memberships cannot access protected resources.

### Organization

- [ ] Organization context is validated.
- [ ] Cross-organization access is blocked.
- [ ] Organization membership is checked server-side.

### Roles

- [ ] Administrator access is correct.
- [ ] Authority access is correct.
- [ ] Inspector access is correct.
- [ ] Contractor access is correct.
- [ ] AI Worker access is restricted.
- [ ] Background Worker access is restricted.

### Permissions

- [ ] Permissions use stable naming.
- [ ] Protected endpoints require explicit permissions.
- [ ] Missing permissions return `403`.
- [ ] Resource-level checks are implemented.

### State

- [ ] Inspection transitions are protected.
- [ ] Maintenance transitions are protected.
- [ ] Repair verification cannot be self-approved.
- [ ] AI cannot create human approval decisions.

### Audit

- [ ] Role changes are audited.
- [ ] Membership changes are audited.
- [ ] Sensitive operational actions are audited.
- [ ] Audit records cannot be modified by normal users.

---

# 39. Future Extensions

The architecture MAY later support:

- Custom organization roles
- Fine-grained resource scopes
- Temporary permissions
- Delegated access
- Approval workflows
- External government identity providers
- Enterprise SSO
- Multi-level administrative hierarchies

These are future extensions and MUST NOT be implemented as part of the initial architecture unless separately approved.

---

# 40. Final Authorization Model

The canonical authorization flow is:

```text
Request
    ↓
Authenticate
    ↓
Resolve User
    ↓
Resolve Organization Membership
    ↓
Resolve Role
    ↓
Check Permission
    ↓
Check Resource Ownership / Organization
    ↓
Check State Transition
    ↓
Allow / Deny
    ↓
Audit Sensitive Action
```

The central security principle is:

```text
AUTHENTICATED
    ≠
AUTHORIZED
```

And:

```text
AUTHORIZED
    ≠
AUTHORIZED FOR EVERY RESOURCE
```

Every protected operation must satisfy:

```text
Identity
+
Active Membership
+
Permission
+
Organization Scope
+
Resource Scope
+
Valid State
```

The platform therefore maintains a controlled chain:

```text
WHO
→ ORGANIZATION
→ ROLE
→ PERMISSION
→ RESOURCE
→ STATE
→ ACTION
→ AUDIT
```

This authorization model is the canonical source of truth for access control across the Road Intelligence & Pothole Management Platform.