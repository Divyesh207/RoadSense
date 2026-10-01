# Road Intelligence & Pothole Management Platform
# Deployment Specification

**Document:** `DEPLOYMENT.md`  
**Version:** 1.0  
**Status:** Approved / Implementation-Ready  
**Project:** Road Intelligence & Pothole Management Platform  
**Primary Deployment Model:** Vercel + VPS + Docker Compose + Supabase  
**Backend:** FastAPI  
**AI Worker:** Celery + Redis  
**Database:** Supabase PostgreSQL + PostGIS  
**Storage:** Supabase Storage  
**Mobile:** Android APK initially, Play Store later

---

# 1. Document Purpose

This document defines the deployment architecture, infrastructure requirements, environment configuration, containerization strategy, networking model, deployment process, security requirements, monitoring, backup strategy, rollback strategy, scaling strategy, and production operations for the Road Intelligence & Pothole Management Platform.

This document is an implementation contract for the coding/deployment agent.

The deployment must remain consistent with:

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
11. `ANDROID_APP_SPEC.md`
12. `SECURITY.md`

If a deployment decision conflicts with one of these documents, the higher-priority source-of-truth hierarchy applies.

---

# 2. Deployment Goals

The deployment architecture must provide:

- Secure HTTPS communication.
- Reliable FastAPI backend hosting.
- Separate AI processing from API request handling.
- PostgreSQL/PostGIS persistence through Supabase.
- Private object storage through Supabase Storage.
- Redis-backed asynchronous processing.
- Dockerized services.
- Simple initial VPS deployment.
- Easy local development.
- Environment separation.
- Reproducible deployments.
- Database migration support.
- Health checks.
- Logging and observability.
- Safe rollback.
- Horizontal scaling capability.
- Future GPU-worker migration.
- No direct database access from web or Android clients.
- No external generative-AI dependency.
- No secrets committed to Git.

---

# 3. Approved Production Architecture

The initial production architecture is:

```text
                         INTERNET
                            |
             +--------------+--------------+
             |                             |
             v                             v
      Next.js Web App                 Android App
         Vercel                       Field App
             |                             |
             +-------------+---------------+
                           |
                         HTTPS
                           |
                           v
                    NGINX / VPS
                           |
                           v
                    FASTAPI API
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
        PostgreSQL       Redis       Supabase Storage
        + PostGIS          |
            ^              |
            |              v
            |         Celery Worker
            |              |
            |              v
            |        AI/ML Pipeline
            |              |
            +--------------+
```

Supabase provides:

```text
PostgreSQL
PostGIS
Storage
```

The VPS provides:

```text
Nginx
FastAPI
Redis
Celery Worker
```

Vercel provides:

```text
Next.js Web Application
```

Android provides:

```text
Field inspection application
```

---

# 4. Deployment Components

## 4.1 Web Application

Technology:

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Framer Motion
- Recharts
- Leaflet
- OpenStreetMap

Deployment:

```text
Vercel
```

Responsibilities:

- Authentication UI.
- Dashboard.
- Road management.
- Inspection review.
- Damage review.
- GIS interface.
- Road health.
- Prediction visualization.
- Maintenance management.
- Repair verification.
- Recurrence management.
- Reports and analytics.

The web application must communicate with the backend through the API.

It must never connect directly to PostgreSQL.

---

# 5. Backend Deployment

The backend is a FastAPI application running inside Docker.

Production flow:

```text
Internet
    ↓
Nginx
    ↓
FastAPI
    ↓
Application Services
    ↓
Repositories
    ↓
Supabase PostgreSQL
```

The API container must not perform long-running AI inference synchronously.

Long-running work must be delegated to the background worker.

---

# 6. AI Worker Deployment

AI processing runs separately from FastAPI.

Architecture:

```text
FastAPI
   ↓
Redis
   ↓
Celery
   ↓
AI Worker
   ├── OpenCV
   ├── YOLO / PyTorch
   ├── Severity Engine
   ├── Road Intelligence
   └── XGBoost
   ↓
PostgreSQL / Storage
```

This separation prevents AI workloads from blocking API requests.

The AI worker must support CPU execution initially.

The architecture must allow future deployment to a GPU-capable machine without requiring major application redesign.

---

# 7. Redis Deployment

Redis is used as the Celery broker and for background-job coordination.

Initial deployment:

```text
Redis container
```

Redis must not be publicly exposed.

Only authorized internal containers may access it.

Example:

```text
FastAPI → redis:6379
Celery Worker → redis:6379
```

Do not expose:

```text
0.0.0.0:6379
```

to the public internet.

---

# 8. Database Deployment

The authoritative database is:

```text
Supabase PostgreSQL
```

with:

```text
PostGIS
```

enabled.

The application accesses PostgreSQL through the backend.

Architecture:

```text
Web
Android
   ↓
FastAPI
   ↓
SQLAlchemy
   ↓
Supabase PostgreSQL
```

Clients must never directly connect to PostgreSQL.

---

# 9. Storage Deployment

Supabase Storage is used for:

- Inspection images.
- Inspection videos.
- Repair evidence.
- Generated reports.
- Model artifacts where appropriate.

Conceptual buckets:

```text
inspection-media
repair-evidence
reports
model-artifacts
```

All sensitive buckets must remain private.

Clients receive short-lived signed URLs where direct upload/download is appropriate.

Never expose:

- Supabase service-role keys.
- Storage administrative credentials.
- Private bucket credentials.

---

# 10. VPS Infrastructure

The initial VPS must run Linux with Docker and Docker Compose.

Recommended baseline:

```text
CPU:      4+ vCPU
RAM:      8+ GB
Storage:  80+ GB SSD
Network:  Stable public internet
OS:       Modern Ubuntu LTS or equivalent Linux
```

These are starting requirements, not hard architectural limits.

AI workloads may require substantially more resources depending on model size and media volume.

The VPS must have:

```text
Docker
Docker Compose
Nginx
Git
TLS certificate tooling
```

installed or provided through containers where practical.

---

# 11. VPS Network Architecture

Only required public ports should be exposed.

Recommended:

```text
22    SSH
80    HTTP
443   HTTPS
```

Internal ports such as:

```text
8000 FastAPI
6379 Redis
```

must not be publicly accessible.

Example:

```text
Internet
   |
   +-- 80/443 --> Nginx
                    |
                    +--> FastAPI :8000
                    |
                    +--> health/internal services
```

SSH access should be restricted using:

- SSH keys.
- Disabled password login where possible.
- Firewall rules.
- Non-root administration.
- Optional IP restrictions.

---

# 12. Docker Compose Architecture

The production Compose stack should conceptually contain:

```yaml
services:
  api:
    ...
  
  worker:
    ...
  
  redis:
    ...

  nginx:
    ...
```

Optional future services may include:

```text
scheduler
monitoring
log aggregation
GPU worker
```

Do not add infrastructure services without a documented requirement.

---

# 13. Container Responsibilities

## 13.1 `api`

Responsibilities:

- FastAPI application.
- Authentication.
- Authorization.
- API validation.
- Database access.
- Storage URL generation.
- Job creation.
- Business logic.
- Analytics APIs.
- Report requests.

Must not:

- Train models.
- Perform large synchronous AI inference.
- Store uploaded media inside the container filesystem permanently.

---

## 13.2 `worker`

Responsibilities:

- Celery worker.
- AI inference.
- Media preprocessing.
- YOLO inference.
- Severity processing.
- XGBoost prediction.
- Repair verification.
- Background processing.

The worker must write results to persistent systems.

Container-local files are temporary.

---

## 13.3 `redis`

Responsibilities:

- Celery broker.
- Background job coordination.

Redis data must not be treated as the authoritative source of business records.

PostgreSQL remains authoritative.

---

## 13.4 `nginx`

Responsibilities:

- TLS termination.
- Reverse proxy.
- Request routing.
- Security headers.
- Request-size control.
- Basic rate limiting where configured.
- Access logging.

Nginx must forward API traffic to FastAPI.

---

# 14. Docker Network

Containers should communicate using a private Docker network.

Conceptually:

```text
road-platform-network

api
worker
redis
nginx
```

Example internal communication:

```text
nginx → api:8000
api → redis:6379
worker → redis:6379
api → Supabase PostgreSQL
worker → Supabase PostgreSQL
api → Supabase Storage
worker → Supabase Storage
```

Only Nginx should require public ingress.

---

# 15. Docker Image Requirements

Production images must:

- Use pinned or controlled base versions.
- Avoid unnecessary packages.
- Run as a non-root user where practical.
- Include only required runtime dependencies.
- Never contain secrets.
- Have predictable startup commands.
- Include health checks where appropriate.

Do not copy:

```text
.env
.git
private keys
local credentials
development databases
```

into production images.

---

# 16. Backend Image

The API image should contain:

```text
Python 3.12+
FastAPI
Uvicorn
SQLAlchemy
Pydantic
Alembic
PostgreSQL driver
Authentication dependencies
Application dependencies
```

Production startup should use an appropriate ASGI process configuration.

Example conceptual command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If multiple workers are required, deployment configuration may use an appropriate process manager or multiple containers.

Do not blindly increase worker count.

Database connections and VPS resources must be considered.

---

# 17. AI Worker Image

The worker image must include:

```text
Python
Celery
Redis client
PyTorch
YOLO
OpenCV
XGBoost
scikit-learn
Pandas
NumPy
FFmpeg where required
AI application code
```

The AI worker must load model artifacts from configured locations.

Models must not be committed directly into Git unless explicitly approved for small development artifacts.

---

# 18. Model Artifact Deployment

Model artifacts must be versioned.

Each deployed model must have:

```text
model_id
model_version
model_type
artifact_reference
status
checksum/integrity metadata where implemented
created_at
approved_at
deployed_at
```

Example:

```text
pothole-detector-v1.2
severity-model-v1.0
deterioration-model-v1.0
repair-verification-v1.0
```

AI results must record the model/version used.

This is required for reproducibility.

---

# 19. Environment Strategy

The project must support:

```text
development
staging
production
```

Environment-specific configuration must never be hardcoded.

Recommended environment files:

```text
.env.example
.env.development
.env.staging
.env.production
```

Actual secret files must never be committed.

---

# 20. Environment Variables

The exact implementation may evolve, but the system must support configuration for:

### Application

```text
APP_ENV
APP_NAME
APP_VERSION
LOG_LEVEL
SECRET_KEY
```

### Database

```text
DATABASE_URL
```

### Authentication

```text
JWT_SECRET
JWT_ACCESS_TOKEN_EXPIRE_MINUTES
JWT_REFRESH_TOKEN_EXPIRE_DAYS
```

### Redis

```text
REDIS_URL
```

### Supabase

```text
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

The service-role key is server-side only.

Never expose it to:

- Next.js browser code.
- Android.
- Public API responses.

### Storage

```text
SUPABASE_STORAGE_BUCKET_INSPECTION_MEDIA
SUPABASE_STORAGE_BUCKET_REPAIR_EVIDENCE
SUPABASE_STORAGE_BUCKET_REPORTS
SUPABASE_STORAGE_BUCKET_MODEL_ARTIFACTS
```

### CORS

```text
CORS_ALLOWED_ORIGINS
```

### API

```text
API_BASE_URL
```

### AI

```text
AI_MODEL_REGISTRY_PATH
YOLO_MODEL_PATH
SEVERITY_MODEL_PATH
PREDICTION_MODEL_PATH
REPAIR_VERIFICATION_MODEL_PATH
AI_DEVICE
```

Possible:

```text
AI_DEVICE=cpu
```

or future:

```text
AI_DEVICE=cuda
```

### Frontend

Only variables explicitly intended for browser exposure may use the frontend public-variable mechanism.

Never expose server-only secrets.

---

# 21. Secret Management

Secrets include:

- JWT secrets.
- Database credentials.
- Supabase service-role credentials.
- Redis credentials if configured.
- SSH keys.
- TLS private keys.
- CI/CD deployment secrets.
- Model artifact credentials.

Secrets must be stored using:

- VPS environment/secret configuration.
- Vercel environment variables.
- GitHub Actions secrets.
- Secure secret management tooling where introduced.

Never store secrets in:

```text
Git
README files
source code
Dockerfiles
logs
screenshots
frontend bundles
Android source
```

---

# 22. Web Deployment

The web application is deployed through Vercel.

Production flow:

```text
GitHub
   ↓
Vercel build
   ↓
Next.js
   ↓
Production Web App
   ↓
FastAPI HTTPS API
```

Required production configuration:

```text
NEXT_PUBLIC_API_BASE_URL
```

Only browser-safe variables may use `NEXT_PUBLIC_*`.

The API base URL must point to the public HTTPS backend.

---

# 23. Android Deployment

Initial Android distribution:

```text
Signed APK
```

Future:

```text
Google Play Store
```

Build variants should support:

```text
debug
staging
release
```

Production builds must:

- Use HTTPS.
- Use production API URL.
- Disable debug logging.
- Exclude test credentials.
- Use signed application builds.
- Protect local authentication/session data.
- Use release configuration.

---

# 24. Domain Architecture

Recommended logical domains:

```text
app.example.com
api.example.com
```

where:

```text
app.example.com → Vercel
api.example.com → VPS / Nginx
```

The actual domain is deployment-specific and must be configured through environment variables.

Do not hardcode production domains in business logic.

---

# 25. HTTPS

Production API traffic must use HTTPS.

Required:

```text
https://api.example.com
```

HTTP should redirect to HTTPS.

TLS certificates must be automatically renewed where possible.

Android must reject insecure HTTP API configuration in production.

---

# 26. Nginx Reverse Proxy

Conceptual flow:

```text
Client
  ↓
HTTPS
  ↓
Nginx
  ↓
FastAPI
```

Nginx should:

- Terminate TLS.
- Forward `X-Request-ID`.
- Preserve relevant proxy headers.
- Enforce upload limits.
- Apply security headers.
- Apply appropriate timeouts.
- Prevent direct access to internal services.

Long-running AI processing must not depend on a client keeping an HTTP connection open.

The API should return a job/processing identifier.

---

# 27. Large Media Upload Architecture

Large media must not be routed unnecessarily through FastAPI.

Preferred flow:

```text
Android/Web
   ↓
FastAPI
   ↓
Signed Upload URL
   ↓
Supabase Storage
```

Then:

```text
Client
   ↓
Upload Complete
   ↓
FastAPI
   ↓
Processing Job
   ↓
Redis
   ↓
AI Worker
```

This prevents large media from unnecessarily consuming API resources.

---

# 28. Database Migration Deployment

Alembic is the migration authority.

Deployment process:

```text
Build application
      ↓
Deploy compatible code
      ↓
Run Alembic migrations
      ↓
Verify migration
      ↓
Start/continue application
```

Migrations must:

- Be version-controlled.
- Be reviewed.
- Be backward-compatible where required.
- Never silently destroy production data.
- Avoid destructive changes without explicit migration planning.

Example:

```bash
alembic upgrade head
```

Never use destructive development reset commands against production.

---

# 29. Deployment Order

A standard production deployment should follow:

```text
1. Build/test
2. Build Docker images
3. Push/version images
4. Backup/verify database where appropriate
5. Deploy compatible API/worker
6. Run database migrations
7. Restart required services
8. Run health checks
9. Verify API
10. Verify worker
11. Verify storage
12. Verify database connectivity
13. Verify critical workflows
14. Monitor logs
```

For schema changes that are not backward compatible, use a staged migration strategy.

---

# 30. CI/CD Pipeline

GitHub Actions should perform:

```text
Code Push
   ↓
Lint
   ↓
Type Check
   ↓
Unit Tests
   ↓
Integration Tests
   ↓
Build
   ↓
Container Build
   ↓
Security Checks
   ↓
Deploy
```

Production deployment should require successful CI.

Do not deploy known failing builds.

---

# 31. Backend CI Checks

Required checks:

```text
Ruff
Pytest
Alembic validation
Type/static checks where configured
Docker build
```

AI worker checks should include:

```text
model loading
inference smoke test
job processing test
artifact validation
```

---

# 32. Frontend CI Checks

Required:

```text
ESLint
Prettier
TypeScript compiler
Vitest
Playwright where configured
Next.js production build
```

---

# 33. Android CI Checks

Required:

```text
Android lint
Unit tests
Instrumentation tests where configured
Build verification
Release build validation
```

---

# 34. Health Checks

The API must provide:

```text
GET /api/v1/health/live
GET /api/v1/health/ready
```

## Liveness

Indicates whether the application process is running.

It should not fail merely because PostgreSQL is temporarily unavailable.

## Readiness

Checks critical dependencies such as:

```text
Database
Redis
Required application configuration
```

The exact dependency set must remain lightweight.

---

# 35. Worker Health

The deployment must provide a way to determine whether the worker is functioning.

Monitoring should detect:

- Worker unavailable.
- Queue backlog.
- Repeated task failures.
- Tasks stuck in RUNNING.
- Model loading failures.

A worker health mechanism may use:

```text
Celery inspection
heartbeat
application health record
monitoring endpoint
```

The implementation should avoid introducing unnecessary infrastructure.

---

# 36. Logging

All production services must generate structured logs.

Minimum fields should include:

```text
timestamp
level
service
environment
request_id
user_id where appropriate
organization_id where appropriate
event
message
```

Sensitive information must not be logged.

Never log:

```text
passwords
JWT tokens
refresh tokens
service-role keys
private storage URLs unnecessarily
full sensitive media
```

---

# 37. Request Correlation

Every API request should have a request identifier.

Preferred:

```text
X-Request-ID
```

If absent, the backend generates one.

The request ID should be propagated to relevant logs and background jobs.

This enables tracing:

```text
API request
→ processing job
→ AI worker
→ database result
```

---

# 38. Background Job Observability

Each processing job must have:

```text
job_id
job_type
status
created_at
started_at
completed_at
error information where appropriate
attempt count
```

AI processing failures must be visible rather than silently swallowed.

---

# 39. Queue Management

Monitor:

```text
queued jobs
running jobs
failed jobs
retry count
processing latency
queue age
```

A growing queue may indicate:

- Insufficient CPU.
- Insufficient GPU.
- Large media volume.
- Model inefficiency.
- Worker failure.

Scaling decisions must be based on measured workload.

---

# 40. Storage Monitoring

Monitor:

```text
storage usage
upload failures
download failures
signed URL generation failures
orphaned media references
```

Database media metadata and storage objects must remain consistent.

---

# 41. Backup Strategy

Supabase/database backup facilities should be used according to the selected production plan.

Critical backup targets:

```text
PostgreSQL database
Application configuration
Model registry metadata
AI model artifacts
Important reports
```

The backup strategy must define:

```text
frequency
retention
storage location
restore procedure
verification procedure
```

Backups are not considered valid until restoration has been tested.

---

# 42. Database Recovery

Recovery must preserve:

- Organizations.
- Users.
- Roads.
- Segments.
- Inspections.
- Original AI detections.
- Human reviews.
- Maintenance history.
- Repair evidence.
- Verification records.
- Recurrence history.
- Audit logs.

Historical records must not be reconstructed by overwriting current values.

---

# 43. Disaster Recovery

Potential failures include:

```text
VPS failure
database failure
Redis failure
worker failure
storage failure
deployment failure
certificate failure
model artifact failure
network failure
```

The recovery process should prioritize:

```text
1. Database integrity
2. API availability
3. Storage accessibility
4. Background processing
5. AI inference
6. Reporting/analytics
```

The exact recovery objectives should be defined according to the production hosting plan.

---

# 44. Redis Failure Handling

Redis is not authoritative.

If Redis fails:

```text
API may remain partially available
AI processing may pause
```

Once Redis is restored:

```text
Workers reconnect
Queued jobs are recovered according to Celery durability/configuration
```

Business records remain in PostgreSQL.

The system must never treat Redis as the permanent source of inspection or damage data.

---

# 45. Worker Failure Handling

If an AI worker crashes:

```text
API remains independently deployable
Jobs remain represented in processing_jobs
Failed/retryable tasks are handled according to retry policy
```

A failed AI job must not corrupt the original inspection evidence.

---

# 46. AI Model Failure Handling

If the configured model cannot load:

```text
AI job → FAILED
```

The system must record the failure.

It must not generate fake AI results.

The inspection must remain available for:

- Retry.
- Human review.
- Diagnostic investigation.

---

# 47. Deployment Rollback

Rollback must support:

```text
Application rollback
Worker rollback
Configuration rollback
Database-compatible rollback
```

Before deployment:

```text
Record version
Record image tag
Record migration version
Record model versions
```

Example:

```text
release-2026.10.01
```

The deployment system should make the previous application image identifiable.

---

# 48. Database Rollback Rule

Database rollback is more sensitive than application rollback.

Do not automatically run:

```text
alembic downgrade
```

in production as a generic rollback mechanism.

Preferred approach:

```text
Backward-compatible migration
+
Previous application version
```

Destructive migrations require explicit recovery planning.

---

# 49. Model Rollback

AI models must be independently versioned.

Example:

```text
YOLO:
v1.2 → v1.3
```

If v1.3 causes unacceptable failures:

```text
deploy v1.2
```

Historical AI results remain tagged with the model version that produced them.

Do not rewrite historical AI outputs merely because a newer model is deployed.

---

# 50. Scaling Strategy

Initial architecture:

```text
1 VPS
 ├── Nginx
 ├── FastAPI
 ├── Redis
 └── AI Worker
```

When load increases:

```text
VPS
 ├── Nginx
 ├── FastAPI replicas
 └── Redis

AI Worker Server
 ├── AI Worker
 └── GPU
```

Supabase remains:

```text
PostgreSQL
PostGIS
Storage
```

---

# 51. Future GPU Worker Architecture

The AI worker must be deployable independently.

Future architecture:

```text
FastAPI
   ↓
Redis
   ↓
GPU AI Worker
   ↓
PostgreSQL / Storage
```

Potentially:

```text
API VPS
     |
     | Redis / secure queue connection
     |
GPU Server
```

The application should not assume the AI worker runs on the same physical machine.

---

# 52. Horizontal API Scaling

FastAPI should remain stateless where practical.

Do not store essential session state inside the API container filesystem.

Shared state belongs in:

```text
PostgreSQL
Redis
Supabase Storage
```

This permits:

```text
API instance 1
API instance 2
API instance 3
```

behind a load balancer when required.

---

# 53. File System Rules

Container filesystem storage is temporary.

Do not permanently store:

```text
uploaded images
videos
reports
repair evidence
database files
```

inside the API container.

Temporary processing files must be:

```text
created
processed
deleted
```

or stored in the appropriate persistent storage.

---

# 54. Time and Time Zones

The backend must use UTC internally.

Database timestamps:

```text
TIMESTAMPTZ
```

Recommended:

```text
UTC
```

Clients may display localized times.

Never compare timestamps using local server time assumptions.

---

# 55. Geographic Deployment Considerations

The platform uses:

```text
WGS84 / EPSG:4326
```

for API-level geographic coordinates unless another documented representation is required.

PostGIS remains authoritative for:

- Road geometry.
- Segment geometry.
- Inspection locations.
- Damage locations.
- Maintenance locations.
- Repair evidence.

---

# 56. OpenStreetMap Usage

The web application uses OpenStreetMap-compatible map tiles through the selected Leaflet mapping configuration.

The deployment must comply with the applicable tile provider's usage requirements.

The application must not assume unlimited public tile usage.

For production-scale usage, the tile provider should be selected and configured according to expected traffic and applicable terms.

---

# 57. CORS

Production CORS must allow only approved web origins.

Example conceptual configuration:

```text
https://app.example.com
```

Do not use:

```text
*
```

for authenticated production APIs unless explicitly justified and secured.

Android does not rely on browser CORS.

---

# 58. API Request Limits

Nginx and FastAPI should enforce appropriate limits for:

- JSON body size.
- Multipart requests.
- Request timeout.
- Upload URL generation.
- Authentication attempts.
- Report generation requests.

Large media should use direct signed storage upload rather than increasing API request limits excessively.

---

# 59. Rate Limiting

Rate limiting should apply to sensitive endpoints such as:

```text
login
refresh
password change
signed URL generation
report generation
AI processing requests
```

Rate limits should distinguish between:

```text
normal users
authenticated users
sensitive operations
```

Exact values should be environment/configuration driven.

---

# 60. Production Security Requirements

Before production deployment:

- HTTPS enabled.
- Firewall configured.
- Redis private.
- Database credentials protected.
- Supabase service-role key server-side only.
- CORS restricted.
- Debug mode disabled.
- Secure headers configured.
- Logs sanitized.
- Secrets absent from repository.
- Production database not resettable through application commands.
- Admin endpoints protected.
- Storage buckets private where required.
- Signed URLs enabled.
- AI artifacts protected.
- Android release build signed.

---

# 61. Production Configuration Validation

The application should fail fast when mandatory production configuration is missing.

Examples:

```text
DATABASE_URL missing
JWT_SECRET missing
REDIS_URL missing
SUPABASE credentials missing
```

must produce a clear startup/configuration error.

Do not silently substitute development defaults.

---

# 62. Development Deployment

Local development should support:

```text
Next.js
FastAPI
Redis
Celery
```

The developer may use local PostgreSQL or Supabase development resources according to the project environment.

The production database must never be used casually for local development.

Example:

```text
Web       → localhost
API       → localhost:8000
Redis     → localhost:6379
```

---

# 63. Staging Deployment

Staging should reproduce production architecture as closely as practical:

```text
Next.js
FastAPI
Redis
Celery
PostgreSQL/PostGIS
Storage
```

Staging must use separate:

- Database.
- Storage.
- Secrets.
- API configuration.
- AI model configuration.

Production data must not be copied into staging without an approved privacy/data-handling process.

---

# 64. Production Deployment Checklist

Before release:

### Code

- [ ] CI passes.
- [ ] Tests pass.
- [ ] Type checks pass.
- [ ] Docker builds successfully.
- [ ] No debug code.
- [ ] No secrets committed.

### Database

- [ ] Migration reviewed.
- [ ] Backup/recovery process verified.
- [ ] Migration tested in staging.
- [ ] No destructive unplanned changes.

### API

- [ ] Health endpoint works.
- [ ] Authentication works.
- [ ] RBAC works.
- [ ] Organization isolation works.
- [ ] Storage upload flow works.
- [ ] Job creation works.

### AI

- [ ] Models load.
- [ ] Model versions are registered.
- [ ] AI smoke test passes.
- [ ] Worker connected to Redis.
- [ ] Failed-job handling works.

### Storage

- [ ] Buckets available.
- [ ] Private access configured.
- [ ] Signed URLs work.
- [ ] Upload/download tested.

### Nginx

- [ ] HTTPS works.
- [ ] HTTP redirects correctly.
- [ ] API routing works.
- [ ] Request limits configured.
- [ ] Security headers configured.

### Web

- [ ] Production API URL correct.
- [ ] Login works.
- [ ] Dashboard loads.
- [ ] GIS loads.
- [ ] Inspection review works.
- [ ] Maintenance workflow works.

### Android

- [ ] Release build signed.
- [ ] Production API configured.
- [ ] HTTPS verified.
- [ ] Login works.
- [ ] Camera works.
- [ ] GPS works.
- [ ] Offline queue works.
- [ ] Sync works.

---

# 65. Post-Deployment Smoke Test

After deployment:

```text
1. Open web application.
2. Login.
3. Verify organization context.
4. Open dashboard.
5. Open map.
6. Create/test inspection.
7. Upload test media.
8. Verify storage object.
9. Verify processing job.
10. Verify worker processing.
11. Verify AI result.
12. Review damage.
13. Create maintenance job.
14. Upload repair evidence.
15. Run repair verification.
16. Verify recurrence/history.
17. Verify audit logs.
18. Verify notifications where configured.
```

The smoke test should use designated test/staging data where possible.

---

# 66. Deployment Verification of Core Lifecycle

The most important production test is:

```text
Field Capture
     ↓
Inspection
     ↓
Media Upload
     ↓
AI Processing
     ↓
Damage Detection
     ↓
Human Review
     ↓
Maintenance
     ↓
Repair Evidence
     ↓
Repair Verification
     ↓
Recurrence
     ↓
Historical Intelligence
```

Every transition must preserve:

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

---

# 67. Monitoring Metrics

Production monitoring should track at minimum:

## API

```text
request count
error rate
latency
5xx rate
authentication failures
```

## Database

```text
connection health
query latency
connection pool usage
storage growth
```

## Redis

```text
availability
queue length
memory usage
```

## AI Worker

```text
jobs processed
jobs failed
processing latency
queue age
model load failures
CPU/GPU utilization
```

## Storage

```text
upload failures
storage usage
signed URL failures
```

## Business

```text
inspections submitted
damages detected
damages reviewed
maintenance jobs created
maintenance jobs completed
repair verification results
recurrence records
```

---

# 68. Alert Conditions

Alerts should be configured for important failures.

Examples:

```text
API unavailable
High 5xx rate
Database unavailable
Redis unavailable
Worker unavailable
Large AI queue
Repeated AI failures
Storage failures
Disk usage critical
Certificate expiration approaching
Repeated authentication failures
```

Thresholds must be configurable according to actual production traffic.

---

# 69. Log Retention

Logs should have defined:

```text
retention period
rotation strategy
storage location
access policy
```

Logs containing sensitive information must be avoided rather than merely relying on retention controls.

Audit logs follow the audit retention policy and must not be treated as ordinary debug logs.

---

# 70. Access Control for Infrastructure

Infrastructure access must follow least privilege.

Roles should be separated where practical:

```text
Developer
Deployment/CI
Infrastructure Administrator
Database Administrator
```

Do not share personal SSH credentials.

CI/CD should use dedicated credentials.

---

# 71. GitHub Actions Deployment Security

GitHub Actions must:

- Use protected secrets.
- Avoid printing secrets.
- Restrict production deployment permissions.
- Prefer short-lived credentials where available.
- Pin critical actions where appropriate.
- Run security checks.
- Prevent arbitrary pull requests from deploying production.

Production deployment should require appropriate branch/environment protection.

---

# 72. Dependency Updates

Dependencies must be periodically updated.

Security updates should be prioritized.

Before upgrading:

```text
Update
→ CI
→ Tests
→ Staging
→ Smoke Test
→ Production
```

AI framework upgrades require additional model inference validation.

---

# 73. Database Connection Management

FastAPI and Celery must use controlled database connection pools.

Avoid:

```text
new database connection per request
```

without pooling.

Connection pool configuration must account for:

```text
Supabase limits
API replicas
worker concurrency
```

The total number of connections must remain within database capacity.

---

# 74. Celery Concurrency

Worker concurrency must be configured based on:

```text
CPU
RAM
GPU
model size
media size
task duration
```

Do not blindly use maximum CPU cores.

For GPU workloads, concurrency must account for GPU memory.

---

# 75. AI Resource Isolation

AI workloads must not consume all resources needed by the API.

If CPU-only inference is initially used:

```text
API resources
+
Redis resources
+
AI worker resources
```

must be planned separately.

If AI processing begins affecting API reliability, move the worker to a dedicated server.

---

# 76. Model Artifact Storage

Model artifacts must not be casually downloaded from untrusted sources at runtime.

Deployment should use:

```text
approved model artifact
+
known version
+
integrity metadata
```

The worker should fail safely if an expected artifact is missing or invalid.

---

# 77. No Runtime Model Training

Production AI workers perform inference.

Model training should occur separately.

Architecture:

```text
Dataset
 ↓
Training Environment
 ↓
Validation
 ↓
Model Registry
 ↓
Approval
 ↓
Deployment
 ↓
Inference
```

Do not train models automatically inside production request processing.

---

# 78. Demo Mode Deployment

Demo mode, if enabled, must be explicitly configured.

It must not:

- Bypass production authentication accidentally.
- Reuse another user's session.
- Mix demo data with real tenant data.
- Expose production records.
- Create fake AI outputs presented as real production inference.

If demo mode is disabled in production, the application must not expose demo-login functionality.

---

# 79. Data Seeding

Production seed data must be extremely limited.

Do not automatically insert fake:

- users
- roads
- damages
- maintenance records
- AI results

into production unless explicitly configured.

Development/staging may use deterministic seed data.

---

# 80. Versioning

Every production deployment should identify:

```text
application version
API version
database migration version
AI model versions
frontend version
Android release version
```

Example:

```text
Application: 1.0.0
API: v1
DB Migration: 20261001_01
YOLO: 1.2
Severity: 1.0
Prediction: 1.0
```

---

# 81. Release Naming

Use predictable release identifiers.

Example:

```text
v1.0.0
v1.1.0
v1.1.1
```

Semantic versioning may be used for application releases.

AI model versions must remain independently identifiable.

---

# 82. Deployment Documentation

Every production release should record:

```text
release version
date/time
deployed by
Git commit
Docker image version
database migration
AI model versions
configuration changes
known issues
rollback version
```

This may be maintained through:

```text
CHANGELOG.md
release notes
deployment records
```

---

# 83. Incident Response

When a production incident occurs:

```text
Detect
 ↓
Assess
 ↓
Contain
 ↓
Recover
 ↓
Verify
 ↓
Document
 ↓
Prevent recurrence
```

For data integrity incidents:

```text
Stop destructive operations
→ preserve evidence
→ identify affected records
→ restore/recover if required
→ verify integrity
→ document incident
```

---

# 84. Security Incident Priorities

Security incidents include:

- Credential exposure.
- Unauthorized database access.
- Cross-organization data exposure.
- Storage exposure.
- Token compromise.
- Model artifact tampering.
- Infrastructure compromise.

Immediate actions may include:

```text
credential rotation
token invalidation
access restriction
service isolation
log preservation
deployment rollback
```

---

# 85. Maintenance Windows

Infrastructure maintenance should be planned when possible.

Potential maintenance activities:

```text
OS updates
Docker updates
database maintenance
dependency updates
model updates
certificate updates
```

Critical security patches may require expedited deployment.

---

# 86. Production Anti-Patterns

The coding/deployment agent must NOT:

- Expose Redis publicly.
- Expose PostgreSQL publicly unnecessarily.
- Put secrets in Git.
- Put Supabase service-role keys in frontend code.
- Put AI credentials in Android.
- Store permanent media in container filesystems.
- Connect clients directly to PostgreSQL.
- Run AI inference synchronously for large media.
- Train models in production requests.
- Use fake AI outputs.
- Ignore failed background jobs.
- Automatically downgrade production databases.
- Reset production databases.
- Disable HTTPS.
- Allow unrestricted production CORS.
- Use wildcard origins unnecessarily.
- Store production credentials in `.env` committed to Git.
- Depend on one container's local filesystem for persistent business data.

---

# 87. Deployment Architecture Invariants

The following are mandatory:

### DEP-INV-001
Web clients communicate with FastAPI through HTTPS.

### DEP-INV-002
Android communicates with FastAPI through HTTPS.

### DEP-INV-003
Clients never directly access PostgreSQL.

### DEP-INV-004
Clients never receive Supabase service-role credentials.

### DEP-INV-005
Redis is private.

### DEP-INV-006
AI processing is asynchronous.

### DEP-INV-007
Original media is stored in persistent object storage.

### DEP-INV-008
AI model versions are recorded.

### DEP-INV-009
Production configuration is environment-driven.

### DEP-INV-010
Production secrets are never committed to source control.

### DEP-INV-011
Database schema changes are managed through Alembic.

### DEP-INV-012
Production deployments are tested before release.

### DEP-INV-013
Rollback does not silently destroy historical data.

### DEP-INV-014
AI failures never generate fabricated results.

### DEP-INV-015
Historical AI results retain their original model/version metadata.

### DEP-INV-016
The deployment can move AI workers to dedicated GPU infrastructure later.

### DEP-INV-017
PostgreSQL remains the authoritative business-data store.

### DEP-INV-018
Supabase Storage remains the authoritative media storage layer.

### DEP-INV-019
Container-local storage is never treated as permanent application storage.

### DEP-INV-020
Production health and failure states are observable.

---

# 88. Coding-Agent Deployment Rules

Any coding/deployment agent implementing this project must:

1. Read all approved architecture documents first.
2. Follow the deployment topology defined here.
3. Not introduce Kubernetes unless architecture is explicitly revised.
4. Not introduce another database without approval.
5. Not replace Supabase PostgreSQL.
6. Not replace FastAPI.
7. Not replace Celery/Redis without an approved architecture change.
8. Not introduce external generative AI APIs.
9. Keep AI processing asynchronous.
10. Keep clients isolated from PostgreSQL.
11. Keep secrets server-side.
12. Use environment variables for deployment configuration.
13. Provide health checks.
14. Provide structured logs.
15. Preserve request IDs.
16. Provide migration-safe deployment.
17. Keep model versions traceable.
18. Document infrastructure changes.
19. Never silently change production behavior.
20. Never fabricate successful deployment or AI processing.

---

# 89. Deployment Definition of Done

Deployment is considered complete only when:

### Infrastructure

- [ ] VPS configured.
- [ ] Docker installed.
- [ ] Docker Compose configured.
- [ ] Nginx configured.
- [ ] Firewall configured.
- [ ] HTTPS configured.

### Backend

- [ ] FastAPI container builds.
- [ ] API starts successfully.
- [ ] Health endpoints work.
- [ ] Database connection works.
- [ ] Redis connection works.
- [ ] Authentication works.

### AI

- [ ] Worker starts.
- [ ] Celery connects to Redis.
- [ ] Approved models load.
- [ ] Test AI job succeeds.
- [ ] Failed AI jobs are visible.
- [ ] Model versions are recorded.

### Database

- [ ] Supabase PostgreSQL configured.
- [ ] PostGIS enabled.
- [ ] Alembic migrations applied.
- [ ] Database permissions verified.
- [ ] Backup/recovery process documented.

### Storage

- [ ] Private buckets configured.
- [ ] Signed URLs work.
- [ ] Inspection media upload works.
- [ ] Repair evidence upload works.
- [ ] Reports storage works.

### Web

- [ ] Vercel deployment succeeds.
- [ ] Production API URL configured.
- [ ] Authentication works.
- [ ] Dashboard works.
- [ ] GIS works.
- [ ] AI review works.
- [ ] Maintenance workflow works.

### Android

- [ ] Release build succeeds.
- [ ] APK is signed.
- [ ] Production API configured.
- [ ] Camera works.
- [ ] GPS works.
- [ ] Offline queue works.
- [ ] Sync works.

### Security

- [ ] No secrets in Git.
- [ ] HTTPS enforced.
- [ ] Redis private.
- [ ] Service-role key protected.
- [ ] CORS restricted.
- [ ] Production debug mode disabled.
- [ ] Storage access secured.

### Operations

- [ ] Logs available.
- [ ] Health checks available.
- [ ] Queue monitoring available.
- [ ] Rollback process documented.
- [ ] Incident procedure documented.
- [ ] Release version recorded.

---

# 90. Final Deployment Architecture

The canonical production deployment is:

```text
                         USERS
                           |
             +-------------+-------------+
             |                           |
             v                           v
       Next.js Web                  Android App
          Vercel                    Field Client
             |                           |
             +------------ HTTPS --------+
                           |
                           v
                    NGINX / VPS
                           |
                           v
                     FASTAPI API
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
     PostgreSQL          Redis       Supabase Storage
     + PostGIS             |
          ^                |
          |                v
          |          CELERY AI WORKER
          |                |
          |        +-------+-------+
          |        |       |       |
          |       v       v       v
          |      YOLO   OpenCV  XGBoost
          |        |       |       |
          +--------+-------+-------+
                           |
                           v
                  HISTORICAL INTELLIGENCE
                           |
                           v
                    MAINTENANCE SYSTEM
                           |
                           v
                  REPAIR VERIFICATION
                           |
                           v
                     RECURRENCE
```

The system must preserve the complete operational chain:

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
MAINTENANCE
 ↓
REPAIR EVIDENCE
 ↓
VERIFICATION
 ↓
RECURRENCE
 ↓
HISTORICAL ROAD INTELLIGENCE
```

This deployment architecture is the canonical initial production architecture for the Road Intelligence & Pothole Management Platform.

Any major infrastructure change must be explicitly documented and reflected in the relevant architecture documents before implementation.