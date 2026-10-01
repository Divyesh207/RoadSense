# SECURITY.md

# Road Intelligence & Pothole Management Platform
## Security Specification

**Document:** 12 — Security Specification  
**Filename:** `SECURITY.md`  
**Status:** Approved for Implementation  
**Version:** 1.0  
**Last Updated:** 2026-10-01

---

## 1. Purpose

This document defines the security architecture, controls, policies, implementation requirements, and security invariants for the Road Intelligence & Pothole Management Platform.

The platform handles:

- User accounts
- Organization and role information
- Road and infrastructure data
- GPS/geospatial information
- Inspection records
- Photographs and videos
- AI-generated detections
- Maintenance records
- Repair evidence
- Repair verification results
- Predictive analytics
- Generated reports
- Audit records

Security must therefore protect:

1. Confidentiality
2. Integrity
3. Availability
4. Evidence authenticity
5. Organization isolation
6. Authorization boundaries
7. AI/model integrity
8. Historical records
9. Operational reliability
10. Auditability

Security is a system-wide requirement and must not be implemented as a final-stage feature.

---

# 2. Security Principles

The implementation must follow these principles.

### 2.1 Defense in Depth

No single security control should be treated as sufficient.

Security must exist across:

```text
Client
↓
Transport
↓
API Gateway
↓
Authentication
↓
Authorization
↓
Application Services
↓
Database
↓
Object Storage
↓
Background Workers
↓
Audit System
```

---

### 2.2 Least Privilege

Every user, service, API endpoint, worker, database credential, and storage credential receives only the permissions required for its function.

Default behavior:

```text
No Permission
    ↓
Explicit Permission Required
    ↓
Allow
```

---

### 2.3 Deny by Default

Unknown or unsupported actions must be denied.

The system must never assume that an authenticated user is authorized to perform an operation.

Authentication answers:

> Who are you?

Authorization answers:

> Are you allowed to perform this action on this resource?

Both checks are required.

---

### 2.4 Server-Side Enforcement

Security decisions must never depend exclusively on:

- Frontend route guards
- Android UI restrictions
- Hidden buttons
- Client-side validation
- Client-provided roles
- Client-provided organization IDs

The backend is authoritative.

---

### 2.5 Organization Isolation

Users belonging to one organization must not access another organization's data unless an explicitly authorized cross-organization capability is introduced in a future architecture revision.

Every organization-owned resource must be associated with an organization.

---

### 2.6 Preserve Evidence

Inspection media, AI detections, human reviews, repair evidence, and verification results are operational evidence.

The system must preserve historical records rather than silently replacing them.

---

### 2.7 Secure by Design

New features must include security requirements before implementation.

Coding agents must not introduce new authentication methods, storage mechanisms, external AI APIs, or privileged services without updating the relevant architecture/security documentation.

---

# 3. Security Scope

Security controls apply to:

- Web application
- Android application
- FastAPI backend
- AI worker
- Celery/background worker
- Redis
- PostgreSQL/Supabase
- PostGIS
- Supabase Storage
- Nginx
- VPS
- CI/CD
- Model artifacts
- Generated reports
- Logs
- Audit records
- Environment configuration

---

# 4. Threat Model

The platform must consider at least the following threat categories.

## 4.1 Authentication Threats

Potential threats:

- Credential theft
- Brute-force login attempts
- Credential stuffing
- Session theft
- Token theft
- Refresh-token abuse
- Account takeover
- Password reset abuse

Required controls:

- Strong password hashing
- Secure token handling
- Rate limiting
- Session expiration
- Secure password-change flow
- Audit logging
- Generic authentication error messages

---

# 5. Authorization Threats

Potential threats:

- Privilege escalation
- Horizontal privilege escalation
- Vertical privilege escalation
- Cross-organization access
- Unauthorized state transitions
- Unauthorized record modification
- Access to restricted reports
- Access to private inspection media

Required controls:

```text
Authenticate
↓
Resolve organization
↓
Resolve membership
↓
Resolve role
↓
Check permission
↓
Check resource organization
↓
Check resource-specific authorization
↓
Check state transition
↓
Allow / Deny
```

---

# 6. Identity and Authentication

## 6.1 Authentication Mechanism

The primary API authentication mechanism is:

```text
JWT Bearer Authentication
```

Requests requiring authentication must include:

```http
Authorization: Bearer <access_token>
```

---

## 6.2 JWT Requirements

JWTs must:

- Use a secure signing algorithm
- Have an explicit expiration
- Include a unique token identifier where required
- Include the user identity
- Avoid storing sensitive information
- Be validated server-side
- Be rejected when expired
- Be rejected when malformed
- Be rejected when signature validation fails

The backend must never trust an unsigned or improperly signed token.

---

## 6.3 JWT Claims

Recommended claims include:

```json
{
  "sub": "user_uuid",
  "iat": 1760000000,
  "exp": 1760003600,
  "jti": "token_uuid"
}
```

Role and organization information may be included when appropriate, but the backend must still validate current membership and authorization.

A stale JWT must not permanently grant access after a user's organization membership or permissions have changed.

---

## 6.4 Token Storage

### Web

Tokens must not be unnecessarily exposed to JavaScript.

Where the authentication implementation permits it, refresh/session credentials should use secure cookie mechanisms with appropriate:

- `HttpOnly`
- `Secure`
- `SameSite`

settings.

Access tokens should have short lifetimes.

---

### Android

Tokens must be stored using secure platform storage.

Do not store:

- JWTs
- refresh tokens
- passwords
- API keys

in plain SharedPreferences, logs, SQLite tables, or application source code.

---

# 7. Password Security

Passwords must never be stored in plaintext.

Use:

```text
bcrypt
```

for password hashing as defined by the approved technology stack.

Password hashes must never appear in:

- API responses
- Logs
- Audit records
- Error messages
- Analytics
- Client applications

---

## 7.1 Password Policy

The backend must enforce a reasonable password policy.

At minimum:

- Minimum length
- Rejection of obviously invalid credentials
- Secure password hashing
- Password confirmation for sensitive password changes where appropriate

The exact policy should be centrally configured rather than duplicated across clients.

---

# 8. Brute-Force Protection

Authentication endpoints must be rate-limited.

Particularly sensitive endpoints include:

```text
POST /auth/login
POST /auth/refresh
POST /auth/change-password
```

The system should detect repeated authentication failures.

Responses should not reveal whether:

- The account exists
- The password was correct
- The organization exists

unless such disclosure is explicitly required by the product behavior.

---

# 9. Role-Based Access Control

The authoritative role model is defined in:

`USER_ROLES_PERMISSIONS.md`

Roles:

1. Administrator
2. Road Authority / Municipal Official
3. Field Inspector
4. Maintenance / Contractor

System actors:

5. AI Worker
6. Background Worker

Authorization must use explicit permissions such as:

```text
roads:read
roads:create
roads:update

inspections:create
inspections:read
inspections:update

damages:read
damages:update
damages:review

maintenance:create
maintenance:update
maintenance:assign

repair_evidence:create
repair_verifications:review
```

The exact permission catalog must remain consistent with `USER_ROLES_PERMISSIONS.md`.

---

# 10. Organization Isolation

Every organization-owned resource must contain an organization relationship either directly or through an authoritative parent relationship.

Examples:

```text
Organization
 ├── Users
 ├── Roads
 │    └── Road Segments
 ├── Inspections
 │    └── Media
 ├── Damages
 ├── Maintenance Jobs
 ├── Repair Evidence
 └── Reports
```

The backend must verify organization ownership before returning or modifying resources.

---

## 10.1 Organization Header

The API supports:

```http
X-Organization-ID: <organization_uuid>
```

The server must:

1. Authenticate the user.
2. Validate the organization ID.
3. Confirm active membership.
4. Resolve the user's role.
5. Check the requested permission.
6. Verify resource ownership.

A client-provided organization ID must never override server-side authorization.

---

# 11. Resource-Level Authorization

Organization membership alone is insufficient.

For every resource request, verify:

```text
User
↓
Organization Membership
↓
Permission
↓
Resource Organization
↓
Resource Access Rule
```

Examples:

- An inspector cannot modify another organization's inspection.
- A contractor cannot edit unrelated road records.
- A user cannot access a maintenance job merely by knowing its UUID.
- A user cannot access private repair evidence through a guessed storage path.

---

# 12. State Transition Security

State machines are security boundaries.

The server must validate every state transition.

### Inspection

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

Failure states:

```text
UPLOAD_FAILED
PROCESSING_FAILED
ANALYSIS_FAILED
```

### Maintenance

```text
OPEN
→ ASSIGNED
→ IN_PROGRESS
→ COMPLETED
→ VERIFICATION_PENDING
→ VERIFIED
```

Alternative transitions include:

```text
IN_PROGRESS → CANCELLED
VERIFICATION_PENDING → REJECTED
REJECTED → IN_PROGRESS
```

Clients must not directly set arbitrary state values.

---

# 13. API Security

All production API traffic must use HTTPS.

Canonical architecture:

```text
Web / Android
      ↓ HTTPS
Nginx
      ↓
FastAPI
      ↓
Application Services
      ↓
Database / Storage / Queue
```

---

## 13.1 Input Validation

All externally supplied input must be validated using backend schemas.

Validate:

- UUIDs
- Strings
- Numbers
- Enumerations
- Dates
- Coordinates
- Geometry
- File metadata
- Pagination
- Filtering
- Sorting
- State transitions

Pydantic validation must be used at the API boundary.

---

## 13.2 SQL Injection Prevention

Never construct SQL queries using unsafe string concatenation.

Use SQLAlchemy parameterized queries and ORM/query mechanisms.

Raw SQL may be used only where necessary and must use parameterized values.

---

## 13.3 Mass Assignment Protection

Clients must not be able to update arbitrary database fields.

Define explicit request DTOs.

For example, a client update should not be able to submit:

```json
{
  "organization_id": "...",
  "created_by": "...",
  "reviewed_by": "...",
  "status": "VERIFIED"
}
```

unless those fields are explicitly allowed for that operation.

Server-controlled fields must remain server-controlled.

---

# 14. API Error Security

Errors must not expose:

- Database passwords
- API keys
- Internal filesystem paths
- SQL statements
- Stack traces
- JWT secrets
- Storage credentials
- Internal infrastructure details

Production API errors must follow the standard contract:

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

Detailed diagnostics belong in protected server logs.

---

# 15. CORS Security

CORS must use an explicit allowlist.

Production configuration must not use:

```text
Access-Control-Allow-Origin: *
```

for authenticated APIs.

Allowed origins must be environment-specific.

Example:

```text
Development:
http://localhost:3000

Production:
https://<approved-web-domain>
```

---

# 16. Rate Limiting

Rate limits should apply to:

- Login
- Token refresh
- Password changes
- Resource creation
- File-upload initialization
- Processing requests
- Report generation
- Expensive analytics
- Prediction requests

Rate limits must be configurable.

Do not hardcode rate limits throughout the codebase.

---

# 17. File Upload Security

The platform accepts photographs and videos, making upload security critical.

## 17.1 Validation

Validate:

- File size
- MIME type
- Extension
- File signature/magic bytes where practical
- Media type
- Image dimensions
- Video duration
- Video codec/container where required

Never trust the filename or extension alone.

---

## 17.2 Storage

Large media must not be stored directly in PostgreSQL.

Use:

```text
Supabase Storage
```

and store only metadata and object references in PostgreSQL.

---

## 17.3 File Names

Do not use user-controlled filenames as direct storage paths.

Generate safe object keys using identifiers such as:

```text
organization_id/
inspection_id/
media_uuid
```

---

## 17.4 Executable Content

Uploads must never be treated as executable code.

The system must reject unsupported executable formats.

---

# 18. Signed Storage URLs

Private inspection media and repair evidence must not be publicly accessible by default.

Access should use short-lived signed URLs.

Flow:

```text
Client
↓
Authenticated API
↓
Authorization Check
↓
Generate Short-Lived Signed URL
↓
Client Downloads/Uploads Object
```

The client must never receive Supabase service-role credentials.

---

# 19. Storage Bucket Security

Conceptual storage buckets:

```text
inspection-media
repair-evidence
reports
model-artifacts
```

Bucket access must follow the principle of least privilege.

The application must enforce organization and resource authorization before generating access URLs.

---

# 20. GPS and Geospatial Data Security

Inspection data contains location information.

Security controls must protect:

- GPS coordinates
- Road locations
- Inspection locations
- Damage locations
- Maintenance locations

Exact coordinates must not be unnecessarily exposed to unauthorized users.

The API must apply role and organization checks before returning geospatial data.

---

# 21. Android Security

The Android application is an evidence collection client and must be treated as an untrusted client.

Never embed:

- Database credentials
- Supabase service-role keys
- JWT signing secrets
- AI model credentials
- Redis credentials
- Internal API credentials

in the APK.

---

## 21.1 Network Security

Production API communication must use HTTPS.

Cleartext HTTP must not be enabled in production.

Debug-only network configuration must not accidentally ship in release builds.

---

## 21.2 Android Permissions

Request only required permissions:

```text
CAMERA
LOCATION
POST_NOTIFICATIONS
```

Permissions must be requested contextually.

Do not request broad storage access unless explicitly required by a future approved feature.

---

# 22. Offline Security

Offline functionality must not bypass authorization.

Offline records must contain:

- Client-generated UUID
- Organization context
- User context
- Creation timestamp
- Local state
- Sync state

When synchronized, the server remains authoritative.

The backend must validate authorization again during synchronization.

---

# 23. Offline Data Protection

Sensitive locally stored data should be minimized.

Where sensitive authentication/session data is stored, use Android secure storage mechanisms.

Local inspection media should:

- Be stored in controlled application storage
- Avoid unnecessary external exposure
- Be deleted only according to the defined lifecycle
- Preserve evidence integrity until successful synchronization where required

---

# 24. AI Security

The AI pipeline is part of the trusted backend infrastructure.

AI models must never be loaded directly from untrusted client input.

The worker must load models from configured trusted artifacts.

---

## 24.1 Model Artifact Security

Model artifacts must be:

- Versioned
- Integrity checked
- Stored outside Git when appropriate
- Access controlled
- Associated with model metadata
- Auditable

Model lifecycle:

```text
DRAFT
→ VALIDATED
→ APPROVED
→ DEPLOYED
→ RETIRED
```

---

# 25. AI Result Integrity

Every AI result must identify:

- Model
- Model version
- Processing run
- Processing timestamp
- Input reference
- Output confidence
- Relevant configuration/version

AI output must not silently overwrite historical results.

---

# 26. Human Review Security

AI output and human decisions must remain distinguishable.

The system must preserve:

```text
Original AI Detection
+
Human Review
+
Final Decision
+
Reviewer
+
Timestamp
```

A human correction must not erase the original AI result.

---

# 27. AI Credential Policy

The core AI system must not depend on:

- OpenAI API
- Gemini API
- Claude API
- Other external generative AI APIs

AI inference must run through the approved local model architecture.

No AI API key may be embedded in:

- Web frontend
- Android APK
- Public repository
- Client-side JavaScript

---

# 28. Background Worker Security

Celery workers and AI workers are privileged backend components.

They must:

- Authenticate to required infrastructure
- Use dedicated credentials
- Have minimum required permissions
- Validate job payloads
- Avoid trusting client-provided authorization claims
- Log job execution
- Avoid exposing secrets in logs

Workers must not directly expose public HTTP endpoints unless explicitly required.

---

# 29. Redis Security

Redis is an internal infrastructure service.

Production Redis must not be publicly exposed.

Use:

- Private network binding
- Authentication where supported/configured
- Strong credentials
- Firewall restrictions
- Environment-specific configuration

Redis must not be used as the permanent source of truth for business records.

---

# 30. Database Security

PostgreSQL is the authoritative structured data store.

Database credentials must:

- Be stored as environment secrets
- Never be committed to Git
- Never be returned through APIs
- Use least-privileged database accounts
- Be rotated when compromised

---

## 30.1 Database Access

Only trusted backend services should access the database.

Architecture rule:

```text
Web
  X
Android
  X
AI Worker ── controlled backend access
API ──────── authorized access
```

Clients must never connect directly to PostgreSQL.

---

# 31. Database Integrity

Use:

- Foreign keys
- Unique constraints
- Check constraints
- Not-null constraints
- Appropriate indexes
- Transaction boundaries

Important relationships must not depend exclusively on application code.

---

# 32. Historical Record Protection

The following records should generally be append-oriented or historically preserved:

- AI processing runs
- AI detections
- Damage reviews
- Road health snapshots
- Maintenance priority snapshots
- Deterioration predictions
- Maintenance status history
- Repair verification results
- Audit logs

The system must not silently rewrite history to make previous results appear different.

---

# 33. Audit Logging

Security-sensitive and operationally significant actions must generate audit records.

Examples:

- Login
- Logout
- Password change
- Role change
- Membership change
- Road creation/update
- Inspection submission
- AI processing
- Damage review
- Damage correction
- Maintenance creation
- Maintenance assignment
- Maintenance completion
- Repair evidence upload
- Repair verification
- Report generation
- Permission-sensitive changes

---

## 33.1 Audit Record

Audit logs should capture, where applicable:

```text
Actor
Organization
Action
Resource Type
Resource ID
Timestamp
Request ID
Relevant Metadata
Result
```

Do not store passwords, tokens, or secrets in audit logs.

---

# 34. Request Correlation

Every API request should have a request identifier.

Header:

```http
X-Request-ID
```

If the client does not provide one, the backend should generate one.

The identifier should appear in:

- API responses where appropriate
- Application logs
- Worker logs
- Error reports
- Audit records where relevant

This enables end-to-end investigation:

```text
Client Request
↓
FastAPI
↓
Database
↓
Redis
↓
AI Worker
↓
Result
```

---

# 35. Logging Security

Logs must never contain:

- Passwords
- Access tokens
- Refresh tokens
- JWT secrets
- Database passwords
- Supabase service-role keys
- API keys
- Private credentials

Avoid unnecessarily logging:

- Full GPS coordinates
- Full uploaded media URLs
- Sensitive user information

Use structured logs.

---

# 36. Secrets Management

Secrets must be supplied through environment configuration or an approved secrets-management mechanism.

Examples:

```text
DATABASE_URL
JWT_SECRET
JWT_REFRESH_SECRET
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
REDIS_URL
STORAGE_CONFIGURATION
```

Exact environment variable names must remain consistent with the deployment specification.

---

## 36.1 Secret Rules

Never:

- Commit secrets to Git
- Put secrets in frontend source
- Put secrets in Android source
- Put secrets in Docker images
- Put secrets in screenshots
- Put secrets in logs
- Put secrets in documentation

`.env` files containing real secrets must be excluded from version control.

---

# 37. Environment Separation

The platform must maintain separate:

```text
Development
Staging
Production
```

Credentials, databases, storage, and service configuration must not be unintentionally shared.

Production data must not be copied into development without an approved sanitization process.

---

# 38. Docker Security

Docker containers must follow least privilege.

Recommended controls:

- Minimal base images
- Non-root application users where practical
- No unnecessary Linux capabilities
- No privileged containers
- Read-only filesystems where practical
- Explicit port exposure
- Internal-only services where possible
- Pinned or controlled dependency versions
- Regular image updates

Redis and internal workers must not expose unnecessary ports publicly.

---

# 39. Nginx Security

Nginx is the public reverse proxy.

It should provide:

- HTTPS termination
- Request size limits
- Basic request filtering
- Security headers
- Rate-limiting support where appropriate
- Reverse proxy routing
- Access logging

Nginx must not expose internal infrastructure ports.

---

# 40. Security Headers

The web application should configure appropriate security headers, including where compatible:

```text
Content-Security-Policy
Strict-Transport-Security
X-Content-Type-Options
Referrer-Policy
Permissions-Policy
Frame-ancestors / X-Frame-Options
```

The exact Content Security Policy must be tested against the Next.js application and required assets before enforcement.

Avoid blindly applying a policy that breaks legitimate functionality.

---

# 41. CSRF Protection

If authentication uses cookies for stateful browser authentication, CSRF protections must be applied to state-changing requests.

If bearer tokens are used without cookies for API authorization, CSRF risk is different, but other token theft protections remain mandatory.

The authentication architecture must document the selected mechanism.

---

# 42. XSS Protection

The web application must:

- Avoid unsafe HTML rendering
- Sanitize user-controlled rich content where required
- Avoid unnecessary `dangerouslySetInnerHTML`
- Encode user-generated content
- Apply an appropriate CSP

User-provided notes, report text, road names, and metadata must be treated as untrusted input.

---

# 43. SSRF Protection

Any backend feature that retrieves a remote URL must validate the target.

The system must not allow arbitrary users to force the backend to request:

- Internal IP addresses
- Metadata services
- Private network endpoints
- Internal administrative services

If remote URL fetching is not required, it should not be implemented.

---

# 44. Path Traversal Protection

User-provided filenames, paths, and object keys must never be directly used as filesystem paths.

Use generated identifiers and controlled storage prefixes.

Reject traversal patterns such as:

```text
../
..\ 
```

and normalize paths before use.

---

# 45. Dependency Security

Dependencies must be regularly reviewed for known vulnerabilities.

Security scanning should be integrated into CI/CD where practical.

Required ecosystems include:

```text
Python
Node.js
Android/Kotlin
Docker
```

Dependency updates must be tested before production deployment.

---

# 46. CI/CD Security

GitHub Actions must follow least privilege.

CI workflows must:

- Avoid unnecessary write permissions
- Protect production secrets
- Avoid printing secrets
- Validate dependencies
- Run tests
- Run static analysis
- Build artifacts reproducibly where practical

Production deployment credentials must not be available to arbitrary pull requests.

---

# 47. Git Security

Repositories must not contain:

- `.env`
- Private keys
- Passwords
- API keys
- Database credentials
- Production tokens
- Service-role credentials

Recommended `.gitignore` coverage includes:

```text
.env
.env.*
!.env.example
__pycache__/
node_modules/
.venv/
build/
dist/
.gradle/
local.properties
```

Model artifacts should not be committed unless explicitly approved.

---

# 48. Dependency and Supply-Chain Security

Third-party packages must be reviewed before introduction.

Coding agents must not automatically add dependencies simply to solve a small problem.

Before adding a dependency, consider:

1. Necessity
2. Maintenance status
3. Security history
4. License compatibility
5. Package size
6. Transitive dependencies
7. Compatibility with the approved architecture

---

# 49. Data Privacy

The system should collect only information necessary for its operational purpose.

Potentially sensitive information includes:

- User identity
- Email address
- GPS coordinates
- Inspection media
- Operational notes
- Maintenance records

Data access must follow:

```text
Need
+
Role
+
Organization
+
Resource authorization
```

---

# 50. Media Privacy

Inspection and repair images/videos may contain:

- People
- Vehicle registration plates
- Private property
- Faces
- Other incidental information

The initial system should avoid unnecessary collection and exposure.

Future privacy enhancements may include automated redaction of sensitive visual information.

Such redaction must not destroy the original evidence without preserving an appropriate original/evidence relationship.

---

# 51. Report Security

Generated reports may contain operationally sensitive information.

Reports must:

- Be associated with an organization
- Have controlled access
- Use private storage
- Use signed download URLs
- Expire signed URLs where appropriate
- Avoid exposing storage credentials

---

# 52. Notification Security

Notifications must not expose unnecessary sensitive information.

Example:

Instead of:

```text
CRITICAL DAMAGE AT EXACT GPS LOCATION: ...
```

use a controlled notification containing only information appropriate to the recipient's role.

Detailed information should require authenticated access to the application.

---

# 53. Search Security

Global search must respect authorization.

Search results must be filtered by:

```text
Organization
+
Permission
+
Resource Access
```

Search indexes must not become an authorization bypass.

---

# 54. Analytics Security

Analytics endpoints must apply the same organization and permission checks as ordinary resources.

Aggregated results must not accidentally expose information from other organizations.

---

# 55. Prediction Security

Deterioration predictions are analytical outputs, not guaranteed outcomes.

Prediction APIs must expose:

- Model version
- Prediction timestamp
- Prediction horizon
- Relevant output
- Feature/input snapshot where appropriate

Users must not be able to modify model outputs directly through ordinary CRUD operations.

---

# 56. Repair Verification Security

Repair verification must preserve the distinction between:

```text
Repair Evidence
↓
AI Verification Result
↓
Human Verification Decision
```

A contractor uploading evidence must not be able to mark the repair as verified.

Verification permissions belong to authorized reviewers.

---

# 57. Recurrence Security

Recurrence records must preserve links to historical damage and repair records.

Users must not be able to delete recurrence history merely because it is operationally inconvenient.

Historical recurrence information must remain auditable.

---

# 58. API Idempotency

Operations susceptible to duplicate execution must support idempotency.

Examples:

- Inspection creation
- Media completion
- Processing requests
- Maintenance creation where applicable
- Report generation
- Offline synchronization

Use:

```http
Idempotency-Key: <unique-key>
```

and client-generated UUIDs where defined.

---

# 59. Replay Protection

Sensitive operations must not be safely repeatable indefinitely using captured requests.

Use:

- Short-lived access tokens
- Expiring signed URLs
- Idempotency keys
- Server-side state validation
- Appropriate timestamps/nonces where required

---

# 60. Security Monitoring

The system should monitor:

- Repeated failed logins
- Unusual authentication activity
- Permission failures
- Cross-organization access attempts
- Repeated invalid requests
- Upload failures
- Worker failures
- Storage access errors
- Database errors
- Unexpected state transitions

Monitoring should distinguish operational failures from security events.

---

# 61. Health Endpoints

Public health checks must reveal minimal information.

Allowed:

```text
/api/v1/health/live
/api/v1/health/ready
```

They should not expose:

- Database credentials
- Redis credentials
- Internal hostnames
- Stack traces
- Environment variables
- Secret configuration

Detailed diagnostics should remain internal.

---

# 62. Security Testing

Security testing must cover:

### Authentication

- Invalid credentials
- Expired token
- Invalid signature
- Missing token
- Token replay scenarios

### Authorization

- Unauthorized role
- Cross-organization access
- Privilege escalation
- Resource ownership violations
- Invalid state transitions

### API

- Injection
- Invalid payloads
- Oversized payloads
- Rate-limit behavior
- CORS behavior
- Error leakage

### Storage

- Unauthorized media access
- Expired signed URLs
- Path traversal
- Malicious file types

### Android

- Secure token storage
- Debug build exposure
- Cleartext traffic
- Offline authorization
- Local data protection

---

# 63. Security Acceptance Criteria

The platform is not security-complete until:

- Authentication works securely.
- Authorization is enforced server-side.
- RBAC matches `USER_ROLES_PERMISSIONS.md`.
- Organization isolation is enforced.
- Clients cannot access PostgreSQL directly.
- Secrets are not present in source code.
- Production API uses HTTPS.
- Storage objects are private by default where appropriate.
- Signed URLs are used for protected media.
- File uploads are validated.
- SQL injection protections are in place.
- State transitions are server-controlled.
- Audit logging is implemented.
- Sensitive actions are traceable.
- AI model artifacts are controlled.
- AI outputs preserve model/version metadata.
- Human review is distinguishable from AI output.
- Historical records are preserved.
- Android does not contain backend secrets.
- Redis is not publicly exposed.
- Internal infrastructure ports are protected.
- CI/CD secrets are protected.
- Security tests exist for critical authorization boundaries.

---

# 64. Security Incident Response

If a security incident is suspected:

```text
Detect
↓
Contain
↓
Preserve Evidence
↓
Assess Impact
↓
Rotate Compromised Credentials
↓
Patch Vulnerability
↓
Validate Fix
↓
Restore Services
↓
Document Incident
```

Potentially compromised credentials must be rotated immediately.

Examples:

- JWT signing secrets
- Database passwords
- Supabase service-role credentials
- Redis credentials
- CI/CD deployment secrets

---

# 65. Credential Rotation

Credentials must be rotatable without modifying application source code.

Configuration must be environment-driven.

Rotation procedures should exist for:

- Database credentials
- JWT secrets
- Storage service credentials
- CI/CD secrets
- Infrastructure credentials

---

# 66. Backup Security

Database backups must be protected with access controls.

Backups must not become a secondary data-leak path.

Where backups contain sensitive information, access must be restricted to authorized infrastructure administrators.

Restore procedures should be tested periodically.

---

# 67. Disaster Recovery

Security also includes availability.

The platform should define:

- Database backup strategy
- Recovery procedure
- Storage recovery strategy
- Infrastructure rebuild procedure
- Credential recovery/rotation process
- Deployment rollback strategy

Recovery procedures must not bypass authorization or integrity controls.

---

# 68. Coding-Agent Security Rules

Coding agents implementing this project MUST:

1. Read all relevant approved documentation before modifying security-sensitive code.
2. Never invent authentication mechanisms.
3. Never add external AI APIs.
4. Never hardcode secrets.
5. Never expose service-role credentials to clients.
6. Never bypass backend authorization for convenience.
7. Never trust client-provided roles.
8. Never trust client-provided organization ownership.
9. Never allow arbitrary state transitions.
10. Never directly expose PostgreSQL to clients.
11. Never make private storage objects public merely to simplify development.
12. Never disable HTTPS security for production.
13. Never remove audit logging from sensitive operations.
14. Never silently delete historical evidence.
15. Never replace AI results without preserving the original result.
16. Never log secrets.
17. Never introduce a dependency without evaluating its necessity.
18. Never use fake security implementations in production code.
19. Never disable validation to make tests pass.
20. Update documentation when a security architecture decision changes.

---

# 69. Security Anti-Patterns

The following are prohibited:

```text
Frontend-only authorization
Client-controlled roles
Client-controlled organization access
Public inspection media
Hardcoded JWT secret
Hardcoded database password
Hardcoded API key
Service-role key in browser
Service-role key in Android
Direct database connection from client
Unauthenticated processing endpoint
Arbitrary state updates
Unvalidated file uploads
SQL string concatenation
Secrets in logs
Secrets in Git
Public Redis
Public PostgreSQL
Permanent storage URLs
Silent historical record deletion
Fake AI verification
```

---

# 70. Security Configuration Principles

Security-sensitive values must be configurable by environment.

Examples:

```text
JWT expiration
Refresh-token expiration
Password policy
Rate limits
Upload limits
Allowed origins
Signed URL expiration
Worker credentials
Database credentials
Redis credentials
Storage configuration
```

Do not duplicate security configuration across frontend, Android, and backend.

The backend remains authoritative.

---

# 71. Security and Observability Relationship

Security events and operational events must be correlated.

Example:

```text
Request ID
    ↓
API Request
    ↓
Authorization Decision
    ↓
Audit Log
    ↓
Background Job
    ↓
AI Processing
    ↓
Result
```

This allows administrators to investigate:

- Who initiated an action
- Which organization it belonged to
- Which resource was affected
- Which request initiated it
- Which worker processed it
- What result was produced

---

# 72. Security Architecture Summary

Canonical security flow:

```text
                    INTERNET
                       │
                      HTTPS
                       │
              ┌────────▼────────┐
              │      NGINX      │
              │ TLS / Limits    │
              └────────┬────────┘
                       │
                ┌──────▼──────┐
                │   FastAPI   │
                └──────┬──────┘
                       │
          ┌────────────▼────────────┐
          │ Authentication          │
          │ Authorization / RBAC    │
          │ Organization Isolation  │
          │ Input Validation        │
          │ State Validation         │
          └────────────┬────────────┘
                       │
        ┌──────────────┼───────────────┐
        │              │               │
   PostgreSQL       Redis          Storage
   + PostGIS                        Private
        │              │               │
        │         Background       Signed URLs
        │           Jobs
        │              │
        │         AI Worker
        │              │
        └──────────────┼───────────────┘
                       │
                 Audit Logging
                       │
                 Historical Data
```

---

# 73. Security Invariants

The following must always remain true:

### INV-SEC-001

An unauthenticated user cannot access protected resources.

### INV-SEC-002

An authenticated user cannot access resources outside authorized organizations.

### INV-SEC-003

A user's client-provided role cannot grant additional permissions.

### INV-SEC-004

Clients cannot directly access PostgreSQL.

### INV-SEC-005

Clients cannot obtain backend service-role credentials.

### INV-SEC-006

Private media requires authorized access.

### INV-SEC-007

AI results identify the model/version that produced them.

### INV-SEC-008

Human review does not erase the original AI result.

### INV-SEC-009

Historical operational records are not silently overwritten.

### INV-SEC-010

Sensitive actions are auditable.

### INV-SEC-011

Secrets never appear in source code or logs.

### INV-SEC-012

State transitions are validated server-side.

### INV-SEC-013

Offline synchronization cannot bypass authorization.

### INV-SEC-014

Repair evidence cannot independently mark a repair as verified.

### INV-SEC-015

Organization isolation is enforced at the backend.

---

# 74. Definition of Done — Security

A security-sensitive feature is complete only when:

```text
Requirement Defined
        ↓
Threat Considered
        ↓
Authentication Checked
        ↓
Authorization Checked
        ↓
Organization Isolation Checked
        ↓
Input Validation Added
        ↓
State Transition Validated
        ↓
Secrets Protected
        ↓
Audit Requirements Checked
        ↓
Error Leakage Checked
        ↓
Tests Added
        ↓
Logs/Monitoring Considered
        ↓
Documentation Updated
```

---

# 75. Final Security Principle

The Road Intelligence & Pothole Management Platform must treat every piece of infrastructure data as part of a trusted operational evidence chain.

The security model therefore protects:

```text
WHO
↓
WHAT
↓
WHERE
↓
WHEN
↓
EVIDENCE
↓
AI MODEL / VERSION
↓
HUMAN REVIEW
↓
MAINTENANCE ACTION
↓
REPAIR EVIDENCE
↓
VERIFICATION
↓
RECURRENCE HISTORY
```

Security is not a separate layer added after implementation.

It is embedded into authentication, authorization, data storage, AI processing, evidence handling, mobile synchronization, infrastructure, auditability, and historical intelligence.

**The platform must remain secure, auditable, organization-isolated, evidence-preserving, and server-authoritative throughout its entire lifecycle.**

---

## End of `SECURITY.md`