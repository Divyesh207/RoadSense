# RoadSense viva preparation

Everything here is taken from the code on `origin/main` (commit `5ed14d5`) and the faculty demo
dataset. Where I could not confirm something from the repository it says **Needs verification**.

The one sentence to remember: **only damage detection is a trained AI model. Severity, road
health, priority, the deterioration estimate and recurrence are fixed rules. Repair verification
is a computer-vision pipeline that uses the same trained detector. A person makes every final
decision.**

---

## 1. What to say

### 30 seconds

> RoadSense is a road condition management platform. A field inspector photographs a road with
> an Android app, which records the GPS position. A trained YOLO model finds potholes and cracks
> in the photos. A reviewer confirms them, and the system then scores road health, ranks repair
> work, tracks the repair, checks before-and-after photos, and watches whether the damage comes
> back. It covers the whole life of a road defect, not only detecting it.

### 1 minute

> Road authorities usually learn about potholes from complaints, and they have no reliable record
> of whether a repair was done properly or lasted. RoadSense addresses that as one connected
> system. The Android app captures photos and GPS, even offline. The backend sends each photo to
> an AI worker where a YOLO11s model, fine-tuned on the Indian subset of the RDD2022 road-damage
> dataset, proposes potholes and cracks. Nothing counts until a human reviewer confirms it.
> Confirmed damage is stored with its location in PostGIS and linked to a road segment. From
> there, documented rules compute a health score, a deterioration risk estimate and a repair
> priority. Maintenance jobs move through a fixed workflow. After the repair, the system compares
> before and after images and a person signs off. If damage reappears within five metres of a
> repaired spot, it is flagged as a recurrence and escalated.

### 3 minutes

Add these points to the 1-minute version:

- **Three clients, one backend.** Android field app, Next.js web console, and a FastAPI backend.
  Neither client touches the database.
- **Asynchronous AI.** Detection takes seconds, so the API puts a job on a Redis queue and a
  Celery worker runs the model. The app polls for the result.
- **Honest labelling.** Every result shows how it was produced: trained model, heuristic
  fallback, rule-based, or human. The model's score is shown as "model confidence", and rule
  outputs are never called predictions.
- **Spatial logic in the database.** PostGIS groups repeat sightings of the same defect (within
  5 m) and finds recurrences near repaired damage.
- **Evidence-based closure.** A repair is not closed by a status change alone. It needs
  after-repair evidence, an automated image comparison, and a human review.
- **Traceability.** Each damage record links back to the detection, the photo and the inspection,
  and forward to the job, the evidence, the verification and any recurrence.
- **Where it stands.** It runs locally with Docker Compose and a physical Android phone. It is
  not deployed to production, and the model has not been validated on Pune roads.

### 5–10 minute presentation flow

1. **Problem (1 min).** Reactive, complaint-driven maintenance; no objective condition record;
   no check that repairs were done or lasted.
2. **Idea (1 min).** Treat a defect as a record with a lifecycle, from capture to recurrence.
3. **Architecture (1.5 min).** Section 3 below.
4. **AI model (1.5 min).** Dataset, classes, threshold, real metrics, limitations. Section 4.
5. **Rules layer (1.5 min).** Severity, health, priority, estimate. Sections 5–7.
6. **Live demo (5–7 min).** Section 12.
7. **Testing, limitations, future (1 min).** Sections 11, 14 and the cheat sheet.

### Who would use it

- Field inspectors (Android app).
- Reviewers and engineers in a road authority (web console).
- Maintenance supervisors and contractors (jobs and evidence).
- Managers (dashboard, reports, audit).

### How it differs from a pothole detection app

A detection app answers "is there a pothole in this photo?". RoadSense also answers: where
exactly, on which segment, how bad, is it the same one seen last week, how healthy is that
road, what should be fixed first, was it fixed, was the fix good, and did it come back.

---

## 2. The lifecycle, stage by stage

| # | Stage | Input | Processing | Output | Technology | Kind |
|---|---|---|---|---|---|---|
| 1 | Data collection | Road, segment, GPS fix, photos | Stored on device, queued, uploaded | Inspection + media on the server | Android: CameraX, Fused Location, Room, WorkManager | Software |
| 2 | Damage detection | Inspection photo | YOLO11s inference at threshold 0.218 | Boxes with class and confidence | Celery worker, Ultralytics/PyTorch | **Trained AI** |
| 3 | Classification | Model classes D00, D10, D20, D40 | Mapping to platform classes | CRACK or POTHOLE | Fixed mapping table | Rule |
| 4 | Severity | Box size, damage class | 0.6 × area factor + 0.4 × class weight | LOW / MEDIUM / HIGH / CRITICAL | Python | **Rule-based** |
| 5 | GPS/GIS mapping | Latitude, longitude | Stored as a PostGIS point | Located detection | PostGIS | Software |
| 6 | Segment association | Road and segment chosen by the inspector | Stored on the record | Damage linked to a segment | PostgreSQL | Software |
| 7 | Human review | Detection promoted to a damage record | Reviewer confirms or rejects, may adjust severity | CONFIRMED or REJECTED | Web console | **Human** |
| 8 | Duplicate grouping | New detection near an open record | Same type within 5 m merges | One record, more sightings | PostGIS `ST_DWithin` | Rule (spatial) |
| 9 | Road health | Active damage, recurrences, traffic class | Capped deductions from 100 | Score 0–100 and band | Python | **Rule-based** |
| 10 | Deterioration estimate | Damage, health, trend, recurrence, repair quality, inspection age, traffic | Hand-weighted sum | Risk 0–100 and band | Python (`rules-v2`) | **Rule-based** |
| 11 | Priority | Severity, sightings, recurrence, prior repairs, health, escalation, estimate | Additive score capped at 100 | Level and score per job | Python (`priority-v2.1.0`) | **Rule-based** |
| 12 | Maintenance | Job with linked damage | Fixed state machine, assignment | Status history | FastAPI | Software |
| 13 | Repair evidence | After-repair photo | Signed upload | Evidence linked to the job | Signed URLs, local storage | Software |
| 14 | Repair verification | Before and after images | Alignment, detector on both, region comparison | SUCCESSFUL / SUBSTANDARD / UNRESOLVED | OpenCV + YOLO | **Computer vision** |
| 15 | Human review of repair | Automated result | Confirm, reject with own result, or unresolved | Final result; job VERIFIED or REJECTED | Web console | **Human** |
| 16 | Recurrence | Newly confirmed damage | Same type within 5 m of repaired damage | Recurrence record with escalation | PostGIS + rules | Rule (spatial) |
| 17 | History | All of the above | Timeline per road and segment | Road intelligence view, reports, audit | FastAPI + web | Software |

---

## 3. Architecture

```
Android field app ──┐
                    ├──> FastAPI backend ──> PostgreSQL + PostGIS
Web console ────────┘         │
                              ├──> Redis (queue) ──> Celery AI worker ──> YOLO11s + OpenCV
                              └──> File storage (signed URLs)
```

| Component | Technology | Why it exists |
|---|---|---|
| Field app | Kotlin, Jetpack Compose, CameraX, Fused Location, Room, WorkManager, Retrofit/OkHttp | Capture evidence on the road, including with no connection |
| Web console | Next.js 14 (App Router), React 18, TypeScript, Tailwind, Recharts, Leaflet, Framer Motion | Review, plan, verify and report |
| Backend | FastAPI, async SQLAlchemy, Pydantic, Alembic | One place for rules, permissions and validation; 92 API routes |
| Database | PostgreSQL 16 + PostGIS 3.4 | Relational data plus spatial queries |
| Queue | Redis + Celery | AI is slow; requests must return immediately |
| AI worker | Ultralytics YOLO11s, PyTorch, OpenCV | Detection and repair image analysis, isolated from the API |
| Storage | Local filesystem with HMAC-signed, expiring URLs. A Supabase Storage backend exists but was tested only against a mocked API | Clients upload and download media without the file passing through JSON APIs |
| Reverse proxy | Nginx (in Docker Compose) | Single entry point |

**Why clients do not access the database directly:** permissions, tenant isolation, validation
and the audit trail all live in the backend. A phone holding database credentials could read
every organization's data.

**Deployment status:** Docker Compose on a laptop (six containers: postgres, redis, api,
ai-worker, web, nginx). The README states production deployment is **not implemented**.

---

## 4. The AI model

| Item | Value |
|---|---|
| Model | YOLO11s (Ultralytics), fine-tuned from `yolo11s.pt` |
| Model id / version | `rdd2022-india-yolo11s` / `india-v1` |
| Dataset | RDD2022, India subset (Arya et al. 2022), CC BY-SA 4.0 |
| Split | 80/10/10 with seed 42: 6,164 train, 770 validation, 772 test images |
| Training | 100 epochs, best epoch 93, image size 640, batch 8, RTX 4060 laptop GPU |
| Classes | D00 longitudinal crack, D10 transverse crack, D20 alligator crack, D40 pothole |
| Mapping | D00, D10, D20 → CRACK; D40 → POTHOLE |
| Not detected | Depression, waterlogging, surface damage, other |
| Threshold | 0.218, chosen on the validation split as the value that maximises mean per-class F1 |
| Score meaning | Uncalibrated model confidence, not a probability of being correct |

### Test results (held-out 10%, not used in training)

| Class | Precision | Recall | mAP50 | Test instances |
|---|---|---|---|---|
| D00 longitudinal crack | 0.48 | 0.26 | 0.30 | 152 |
| D10 transverse crack | 0.00 | 0.00 | 0.006 | 6 |
| D20 alligator crack | 0.58 | 0.59 | 0.59 | 215 |
| D40 pothole | 0.58 | 0.35 | 0.41 | 335 |
| **Overall** | **0.41** | **0.30** | **0.33** | |

Overall mAP50-95 is 0.13. At the deployed threshold, pothole precision is 0.53 and recall 0.40.

**How to say it:** "The model is modest. It finds about four in ten potholes in the test set,
and about half of what it flags is right. That is why a human reviews every detection. The
platform is built so a better model can be dropped in without changing anything else."

**D10 is effectively undetected.** There are only 53 transverse-crack examples in training and
6 in the test set. Say this before you are asked.

### Why RDD2022 India

- Public, citable, with bounding-box labels for the damage types we need.
- Indian road scenes (surface, traffic, lighting) are closer to our conditions than other
  countries' subsets.
- It let us train and measure honestly on a held-out split.

**It is not Pune data.** The images are from other Indian cities, captured from a vehicle-mounted
phone. Accuracy on Pune roads and on hand-held photos is unmeasured. Validating that needs
labelled Pune images.

### When detection is unavailable

- If trained weights cannot be loaded, the worker can fall back to an **OpenCV contour
  heuristic**. It is not a trained model, and its output is labelled "Heuristic fallback" with a
  "heuristic score, not a probability".
- The running stack sets `AI_REQUIRE_TRAINED_MODEL=true`, which disables the fallback: the job
  fails instead of silently using the heuristic.
- All 46 detections in the faculty demo are from the trained model.

### Provenance shown to users

Each detection and damage record carries the detection method, the score type, the model name
and version. The UI labels them "Trained model", "Heuristic fallback", "Manual entry",
"rule-based" and "human review".

---

## 5. Severity (rule-based)

```
area_factor = min(1, box_area_fraction / 0.15)
score       = 0.60 × area_factor + 0.40 × class_weight
class_weight: POTHOLE 0.85, CRACK 0.50
≥ 0.75 CRITICAL · ≥ 0.50 HIGH · ≥ 0.25 MEDIUM · else LOW
```

Example: a pothole whose box covers 3% of the image. Area factor 0.03 / 0.15 = 0.2.
Score = 0.6 × 0.2 + 0.4 × 0.85 = 0.46 → MEDIUM.

It uses the box size in the image, not real-world size. Physical area is not estimated because
there is no camera calibration. A reviewer can override the severity.

---

## 6. Road health (rule-based, not machine learning)

Start at 100 and subtract:

| Item | Per item | Cap |
|---|---|---|
| CRITICAL damage | 25 | 60 |
| HIGH damage | 15 | 45 |
| MEDIUM damage | 7 | 35 |
| LOW damage | 2.5 | 20 |
| Active recurrence | 5 | 25 |

The damage deductions are multiplied by a traffic factor **only if a documented traffic class
exists** (LOW 1.0, MEDIUM 1.1, HIGH 1.2, VERY_HIGH 1.3; unknown = 1.0, never estimated).
Recurrence is added after that.

Bands: ≥ 80 GOOD, ≥ 60 FAIR, ≥ 40 POOR, below 40 CRITICAL. No inspection and no damage gives
INSUFFICIENT_DATA instead of a score.

Only active damage counts (detected, confirmed, scheduled, in progress). Rejected and repaired
damage does not, and neither does damage still awaiting review.

**Worked example from the demo (Akurdi Main Road, segment 3):** one CRITICAL pothole (25) and one
HIGH crack (15) = 40. Traffic class HIGH → 40 × 1.2 = 48. Health = 100 − 48 = **52, POOR**. That
is the value on screen.

A road's score is aggregated from its segments. **Needs verification:** the exact weighting
(the code keeps a weights list; in the demo all segments have similar lengths, so it reads as a
plain average: (65 + 82 + 52) / 3 = 66.3).

Version shown in the UI: `health-v1.1.0`.

---

## 7. Deterioration estimate and priority (both rule-based)

### Deterioration estimate (`Rule-Based-Deterioration-Estimate`, `rules-v2`)

A risk score from 0 to 100, as a sum of itemised contributions:

| Contribution | Rule | Cap |
|---|---|---|
| Damage severity | 20 per critical, 12 per high, 5 per medium, 1.5 per low | 50 |
| Health deficit | 0.3 × (100 − health) | 30 |
| Health trend | From observed decline, needs snapshots at least 7 days apart | 15 |
| Recurrence | 6 per recurrence, plus 4 per escalated one | 18 + 8 |
| Repair quality | SUBSTANDARD 8, UNRESOLVED 4 | |
| Inspection age | days / 45 | 8 |
| Traffic | 0 / 1.5 / 3 / 5 by class, only if documented | |

The sum is multiplied by a horizon factor (1 + 0.25 × days / 365). Bands: below 25 LOW, below 50
MODERATE, below 75 HIGH, otherwise SEVERE.

There is no trained model, no training data and no confidence value. A future health number is
given only as a straight-line extrapolation when an observed trend exists. The code reports how
much history exists for training a real model; it requires at least 30 segments with health
measured 30 days apart, which we do not have.

### Priority (`priority-v2.1.0`)

```
score = severity base
      + 2 per repeat sighting              (max 10)
      + 5 per active recurrence            (max 15)
      + 4 per earlier verified repair      (max 12)
      + 0.15 × (100 − health)              (max 15)
      + 5 (ELEVATED) or 10 (CRITICAL) recurrence escalation
      + 0.1 × deterioration risk, if under 30 days old (max 10)
capped at 100
```

Severity base comes from the worst linked damage: CRITICAL 85 + 2.5 per damage; HIGH 65 + 3 per
damage (max 84); MEDIUM 40 + 3 (max 64); LOW 20 + 2 (max 39).
Bands: ≥ 85 CRITICAL, ≥ 65 HIGH, ≥ 40 MEDIUM, else LOW. The level is never lower than the worst
damage's severity. A priority set manually by a person is never overwritten.

**What "CRITICAL 100" means (rank 2 in the demo, Akurdi Main Road segment 3):** severity base
90 (critical, two damages) + frequency 4 (two repeat sightings) + road health 7.2
(0.15 × 48) = 101.2, capped at 100.

**Why not just count potholes:** one critical pothole on a busy, already poor road that has been
repaired before and came back should outrank five minor cracks on a healthy lane. The score
shows every component, so the ranking can be explained and challenged.

---

## 8. Repair verification and recurrence

### Repair verification (algorithm `repair-cv-v1.0.1`)

1. **Quality checks** on both images: size, exposure, sharpness.
2. **Alignment:** ORB features, ratio-test matching, RANSAC homography that maps the AFTER image
   onto the BEFORE image, with sanity checks.
3. **Detection:** the trained YOLO model runs on both images. BEFORE detections define where the
   damage was.
4. **Comparison** inside the damage region against the surroundings: SSIM, normalised difference,
   edge density.
5. **Decision by fixed rules.**

| Result | Meaning |
|---|---|
| SUCCESSFUL | The damage region changed and the detector finds nothing there afterwards |
| SUBSTANDARD | The detector still finds damage overlapping the original region |
| UNRESOLVED | The evidence cannot support a decision: images do not align, poor quality, no damage found in BEFORE, or nothing changed and nothing detected |

**Automated analysis versus human review.** The automated result is a measurement. It never
changes the job. A reviewer then confirms it, rejects it with their own result and a written
reason, or marks it unresolved. The automated row is kept unchanged and the human decision is
stored as a separate row. The human decision moves the job to VERIFIED or REJECTED.

**Limitation to state plainly:** it has only been run on constructed image pairs. In the demo the
BEFORE images are real RDD2022 photos and the AFTER images are edited copies of them. It has not
been validated on photographs of real repairs.

### Duplicates and recurrence

- **Duplicate prevention:** a new detection of the same type within 5 m of an open damage record
  is added to that record as another sighting. The radius is a setting.
- **Recurrence:** when damage is confirmed, the system looks for earlier damage that is in the
  same organization and segment, within the same radius, of the same type, and was actually
  repaired. A match becomes a recurrence record with status POTENTIAL until a person reviews it.
- **Escalation rules:** repeated recurrence at the spot, a previous repair that was not verified
  SUCCESSFUL, recurrence within 90 days, or high/critical severity. Levels: NONE, ELEVATED,
  CRITICAL. Every rule that fired is stored and shown.

**Demo scenarios:** on Akurdi Main Road segment 1 a pothole was repaired and verified, then found
again 1.06 m away; it is confirmed and escalated to CRITICAL, and a re-repair job is open. On Pune
Demo Connector segment 1 the same pattern is ELEVATED and awaiting review. On Akurdi College Road
segment 2 the follow-up inspection found nothing, so there is no recurrence.

---

## 9. Android app and web console

### Android field workflow

Login → pick road and segment → acquire GPS (coordinates and reported accuracy) → take photos →
save as draft or queue → background upload → server-side AI → results on the detail screen.

- **Offline:** inspections and photos are stored in Room on the device. Queued items upload when
  a connection exists.
- **WorkManager:** runs the upload as background work with a "network connected" constraint, so
  it survives the app being closed and retries later.
- **Upload path:** create inspection → request a signed upload URL → PUT the photo → confirm →
  submit → request processing.
- **Session:** tokens are kept in EncryptedSharedPreferences; an expired access token is
  refreshed automatically.
- **Not in the app:** video capture, repair-evidence capture, and account creation (the Create
  Account screen only validates input; the server has no registration endpoint).
- **Local setup, if asked:** the debug build talks to `http://127.0.0.1:8000/` and reaches the
  laptop through `adb reverse` over USB. That is a development arrangement, not a deployment.

### Web console modules

| Module | Shows | Why |
|---|---|---|
| Dashboard | Counts of roads, active damage, jobs, verifications, recurrences, average health | One-screen status |
| Roads & Segments | Road list, segments, health per segment, timeline; add road and segment with map drawing | The network the data hangs on |
| Field Inspections | Inspections, processing state, detections with provenance | See what came from the field |
| Damage Intelligence | Damage records, source, score, review queue | Human review of AI output |
| Priorities | Ranked open jobs with every scoring component | Explainable ordering |
| Maintenance Operations | Board of jobs by state, assignment, history | Run the work |
| Repairs & Verification | Automated result, human review, before/after viewer | Evidence-based closure |
| Recurrence | Investigation chain per record, escalation reasons | Find repairs that failed |
| Spatial Map | Damage, segments by health, inspection points, filters | Where things are |
| Reports & Exports | PDF, CSV, JSON generated from stored records | Hand-off to management |
| Audit & Security | Who did what, when, with before/after values | Accountability |

---

## 10. Database, GIS and security

### Why PostgreSQL + PostGIS

The data is relational (organization → road → segment → inspection → detection → damage → job →
evidence → verification) and spatial. PostGIS stores points and lines and answers distance
questions inside the database with an index:

- "Is there an open pothole within 5 m of this detection?" (duplicate grouping)
- "Was there repaired damage within 5 m of this new one?" (recurrence)
- Map layers and geometry for roads and segments.

Distances are computed on geography, so they are in metres, not degrees.

### Multi-tenancy

Every business table has an `organization_id`. Each request carries the organization in a
header, the backend checks the user is a member, and every query filters by it. The faculty demo
lives in its own organization; the other organization's data is invisible to it.

### Security answers

| Topic | What is implemented |
|---|---|
| Authentication | Email and password; JWT access token (HS256, 60 minutes) plus a refresh token (30 days) stored only as a SHA-256 hash |
| Passwords | bcrypt, 12 rounds |
| Authorization | Permission check on each route. Only the ADMINISTRATOR role is seeded, and it has full access. Other roles and their permission sets are not configured |
| Tenant isolation | Organization filter on every query, verified by tests |
| Media | HMAC-signed URLs that expire (15 minutes for uploads). The signature covers method, bucket, path and expiry |
| Rate limiting | Sliding window per client address: 30 login attempts and 300 other requests per minute |
| Other | Security headers, request size limits, audit log |

**The rate-limiter story, if asked about testing:** on the CI server 28 tests failed with HTTP
429. The limiter keeps its history in memory, and the whole test suite runs in one process from
one address, so tests that log in shared a single 30-per-minute window. The fix clears that
history before each test. The limits were not changed. While doing it, a request header that let
any client skip the limiter was found and removed, and a test now proves it no longer works.

**Limits to admit:** the limiter is in memory, so it is per process and would not be shared
across several API servers. There is no TLS or secret management set up.

---

## 11. Testing

Do not say "we have 275 tests". Say what they check.

| Suite | Count | What it validates |
|---|---|---|
| API (pytest) | 192 | Auth and tokens, tenant isolation, roads/segments, inspections and uploads, damage promotion and review, GPS grouping, health, estimates, priority, maintenance state machine, repair evidence and verification workflow, recurrence, analytics and reports, storage signing, security hardening, and one full lifecycle test |
| Rate limiting (inside the 192) | 14 with the hardening file | Below-limit requests pass, the limit returns 429 in the standard envelope, login has its own limit, clients are limited separately, defaults are 30 and 300, no header bypasses it |
| AI worker (pytest) | 51 | Detector and model registry, pre-processing, duplicate suppression, severity rule, inspection pipeline, repair-verification analysis on constructed pairs |
| Web (vitest) | 16 | Helper logic: geometry, permissions, intelligence and repair helpers, demo-form validation |
| Static checks | | TypeScript typecheck clean, ESLint exit 0, Ruff clean, production web build succeeds |
| PostGIS integration | 6 tests | Run against a real PostgreSQL 16 + PostGIS 3.4 in CI. **Needs verification:** I did not run these locally in this session |

The API unit tests use an in-memory SQLite database with spatial functions emulated; the real
PostGIS behaviour is covered by the integration tests and by the live demo seed.

**What the tests do not prove:** real-world detection accuracy, or repair-verification accuracy on
real repairs. They prove the software behaves as designed.

**GitHub Actions status after the last merge: Needs verification** (check the Actions tab).

---

## 12. Live demo script (5–7 minutes)

Sign in at `http://localhost:3000/login` with the demo supervisor account. Before you start,
say: "This is a demonstration dataset. The photos are public RDD2022 images, the locations are
demo coordinates around Akurdi, and all the processing you see is the real pipeline."

| # | Click | Say | Demonstrates | Likely follow-up |
|---|---|---|---|---|
| 1 | Login | "JWT login; this account belongs to the demo organization." | Auth, tenancy | How are passwords stored? |
| 2 | Dashboard | "5 roads, 11 segments, 17 active damage records, 15 jobs, 2 recurrences. Every number is counted from records." | Aggregation | Is this real-time? (It loads on open; no auto-refresh.) |
| 3 | Spatial Map → click a red marker on Akurdi Main Road | "Type, severity, model confidence, coordinates, segment." Filter CRITICAL, reset. | PostGIS, provenance | How accurate is the GPS? |
| 4 | Roads & Segments → DEMO - Akurdi Main Road | "Segments at 65, 82 and 52. Segment 3 is POOR." | Road model | How is 52 calculated? (Section 6.) |
| 5 | Scroll to the deductions and timeline | "The score shows its deductions; the timeline shows every event." | Explainability | Is this machine learning? (No.) |
| 6 | Damage Intelligence | "24 from the trained model, 1 entered by a person. 3 await review, 2 were rejected as false positives." | Human review | What about false negatives? |
| 7 | Priorities → rank 2 | "CRITICAL 100: severity 90, repeat sightings 4, road health 7.2." | Rule-based scoring | Why these weights? |
| 8 | Maintenance → "Pothole repair, Akurdi Main Road seg 1" | "Assigned to a contractor; status history from OPEN to VERIFIED." | State machine | Can a step be skipped? (No.) |
| 9 | Repairs & Verification → Compare on that job | "Before and after, zoom together. The after image is a constructed demo image." | Evidence | Is that a real repair? (No, say so.) |
| 10 | Same modal, left panel | "Automated analysis: SUCCESSFUL, detector 1 before, 0 after." | CV pipeline | How does alignment work? |
| 11 | Same modal, right panel; then the College Road seg 1 row | "A person confirmed this one. Here the reviewer rejected a SUCCESSFUL result." | AI ≠ human decision | Who is accountable? |
| 12 | Recurrence | "Repaired, verified, then found again 1.06 m away. Escalated to CRITICAL; a re-repair job is open." | Spatial rule | Why 5 m? |
| 13 | Reports → download the Executive PDF | "Generated from the same records." | Reporting | Formats? (PDF, CSV, JSON.) |
| 14 | Audit & Security | "Who confirmed which damage, who reviewed which verification." | Accountability | Can logs be edited? (**Needs verification.**) |
| 15 | Phone: Home → New → Queue | "Road, GPS, photos, queue. Works offline and uploads later." | Offline-first | What if upload fails? (Stays queued; retry.) |

Check before the session: Docker running, demo seeded, the before/after images load, phone
connected with the tunnel script running.

---

## 13. Viva questions and answers

Format: **Q** · short answer · *if pressed* · technical detail.

### A. Problem statement

**Q1. What problem does this solve?**
Road defects are found late, repaired without proof, and often return. *If pressed:* there is
usually no link between the complaint, the repair and its outcome. Technical: we model the
defect as a record with a lifecycle and keep every link.

**Q2. Who is the user?**
A road authority: inspectors, reviewers, maintenance engineers, managers. *If pressed:* the
Android app is for the field, the web console for the office.

**Q3. Is this needed when citizens already report potholes?**
Complaints say where people are annoyed, not the condition of the network. *If pressed:* we add
systematic inspection, objective scoring and repair verification.

### B. Innovation

**Q4. What is new here?**
The closed loop: detection, review, health, priority, repair verification and recurrence in one
traceable system. *If pressed:* detection alone is common; verifying repairs and tracking
recurrence with spatial rules is the distinguishing part.

**Q5. Isn't this just YOLO on road images?**
YOLO is one of seventeen stages. *If pressed:* remove the model and the platform still manages
manually reported damage end to end.

**Q6. What is the most technically interesting part?**
Repair verification: aligning two photos and comparing only the damaged region. Technical: ORB,
RANSAC homography, SSIM, plus the detector on both images.

### C. Architecture

**Q7. Why separate the AI worker from the API?**
Inference is slow and heavy; the API must stay responsive. Technical: Celery tasks on a Redis
queue, with job status the client can poll, retries and idempotent jobs.

**Q8. Why FastAPI?**
Python, so it shares a language with the AI code; async; automatic validation and docs.
*If pressed:* Pydantic schemas validate every request.

**Q9. Why not Firebase?**
We need relational integrity, spatial queries and server-side rules. *If pressed:* "damage within
5 m" is one indexed PostGIS query; in a document store we would write and maintain that
ourselves, and tenant rules would be harder to enforce.

**Q10. What happens if the worker is down?**
The inspection stays submitted and the job stays queued; nothing is lost. *If pressed:* jobs have
attempt counts and a failed state.

### D. AI / ML

**Q11. Which parts are actually AI?**
Only damage detection. *If pressed:* severity, health, priority and the estimate are rules;
verification is classical computer vision plus the same detector.

**Q12. Why YOLO?**
It is a single-stage detector: fast, well supported, and it gives boxes, which we need for
locating damage in the image. *If pressed:* we need localisation, not only classification.

**Q13. Why YOLO11s and not a larger model?**
It trains on a laptop GPU (2.7 GB peak) and runs on CPU in the worker. *If pressed:* a larger
variant might score higher; we did not compare variants. **Needs verification** if you claim
any comparison.

**Q14. What accuracy do you get?**
mAP50 0.33 overall, 0.41 for potholes, on a held-out test split. Precision 0.41, recall 0.30.
*If pressed:* it is modest, which is why review is mandatory.

**Q15. How was the threshold chosen?**
0.218, the confidence that maximises mean per-class F1 on the validation split, not the test
split.

**Q16. Is the confidence a probability?**
No. It is an uncalibrated model score, and the UI says so.

**Q17. Is your prediction machine learning?**
No. It is a hand-weighted rule-based estimate and is labelled that way everywhere.
*If pressed:* a trained model needs outcome history we do not have; the code measures how much
exists and refuses to pretend.

**Q18. Is road health AI?**
No. It is a deduction formula. I can compute any score by hand (section 6).

### E. Computer vision

**Q19. How do you compare before and after photos taken from different positions?**
We find matching feature points and compute a homography that warps one onto the other.
Technical: ORB keypoints, Lowe ratio test at 0.75, RANSAC, with checks on scale, perspective and
overlap.

**Q20. What if the two photos show different places?**
Alignment fails and the result is UNRESOLVED. The demo has that case.

**Q21. What is SSIM?**
A structural similarity measure between two image regions. We use it to see whether the damaged
region changed more than its surroundings.

**Q22. What is the heuristic fallback?**
An OpenCV contour rule used only if trained weights are missing. It is disabled in our stack and
always labelled.

### F. Dataset

**Q23. Why RDD2022?**
Public, labelled, includes India. *If pressed:* it is not Pune.

**Q24. Did you test on training data?**
No. The split is 80/10/10 with a fixed seed, and metrics are on the held-out 10%.

**Q25. Why is D10 so poor?**
53 training examples and 6 test examples. The class is too rare to learn.

**Q26. Are the demo images in the training set?**
No. The demo uses RDD2022's official test images, which have no released labels and were not
used for training or evaluation.

### G. Database

**Q27. Why PostgreSQL?**
Relational integrity plus PostGIS. *If pressed:* migrations with Alembic, additive only.

**Q28. How are organizations separated?**
`organization_id` on every table and a membership check on every request.

**Q29. How is history kept?**
Status history tables, health snapshots, separate rows for automated and human verification,
and an audit log. Records are not overwritten to hide earlier states.

### H. GIS / PostGIS

**Q30. How do you prevent duplicate potholes?**
Same type within 5 m of an open record is merged as another sighting.

**Q31. What if GPS is inaccurate?**
Phone GPS is typically several metres off, and we store the reported accuracy. *If pressed:* poor
GPS can split one defect into two records or miss a recurrence. The radius is configurable, and
the inspector also selects the road and segment by hand.

**Q32. Why not Google Maps?**
Google Maps is a map display and routing service. We need to store our own geometry and run
distance queries on it. The console uses Leaflet with OpenStreetMap tiles for display only.

**Q33. Why 5 metres?**
A practical default near phone GPS accuracy. It is a setting, not tuned on field data.

### I. Backend

**Q34. How is the maintenance workflow enforced?**
A table of allowed transitions on the server. An invalid jump returns an error.

**Q35. How are large photos uploaded?**
The client gets a signed URL and uploads the file directly; only metadata goes through JSON.

### J. Android

**Q36. What happens without internet?**
Capture continues; data is stored in Room and uploaded by WorkManager when connected.

**Q37. Why WorkManager?**
It guarantees deferred background work under constraints, across app restarts.

**Q38. Does the AI run on the phone?**
No. Inference runs on the server.

### K. Web

**Q39. Why Next.js?**
React with routing and production builds out of the box, and TypeScript for safety.

**Q40. How do you avoid misleading users about AI?**
Every value is labelled with its source, and unreviewed detections are shown as candidates.

### L. Security

**Q41. How are passwords stored?**
bcrypt hashes with 12 rounds.

**Q42. What stops brute-force login?**
30 login attempts per minute per client address.

**Q43. What roles exist?**
Only administrator is configured. The permission mechanism exists; other roles are not set up.

### M. Testing

**Q44. How did you test?**
Automated suites for the API, worker and web, plus a live end-to-end run through the real stack
(section 11).

**Q45. Did tests find real bugs?**
Yes: the shared rate-limit window in CI, and the bypass header found while fixing it.

### N. Deployment

**Q46. Is it deployed?**
No. It runs with Docker Compose on a laptop.

**Q47. Can it work at city scale?**
The design allows it, but it is not demonstrated. *If pressed:* the worker can be scaled out and
PostGIS is indexed, but there is no load test, the rate limiter is per process, and storage is
local disk.

### O. Limitations

**Q48. How do you handle false positives?**
Human review; rejected records are excluded from health and priority.

**Q49. How do you handle false negatives?**
The model misses most damage (recall 0.30). Mitigations: an inspector can add damage manually,
and repeat inspections give more chances. It remains the main limitation.

**Q50. What are the main limitations?**
See section 14.

### P. Future scope

**Q51. What next?**
Collect and label Pune images and retrain; validate repair verification on real repairs; train
a deterioration model once history exists; configure roles; deploy with HTTPS.

**Q52. How would you train on Pune roads?**
Capture with the field app, label boxes for the four classes, add them to the training set,
fine-tune from the current weights, and report metrics on a held-out Pune test split.

**Q53. Why do you need AI at all?**
Looking at thousands of photos by eye does not scale. The model pre-screens and points at
candidates; people decide.

---

## 14. Claims I must NOT make

- Do not call the deterioration estimate, road health, priority or severity "AI" or "ML".
- Do not say the model is accurate. Say mAP50 0.33, recall 0.30, and that review is mandatory.
- Do not say the model is trained or validated on Pune roads.
- Do not say transverse cracks are detected.
- Do not say the model detects depressions, waterlogging or surface damage.
- Do not say repair verification is validated on real repairs.
- Do not say the after-repair images are real, or that the RDD2022 photos were taken in Akurdi.
- Do not present the demo coordinates, dates or traffic figures as real measurements.
- Do not say the system is deployed, in production, or used by any authority.
- Do not say "real-time". The dashboard loads when opened.
- Do not claim role-based access with multiple roles; only administrator exists.
- Do not claim users can register; accounts are created by an administrator.
- Do not claim PCI or any standard compliance, RTK GPS, or video inspection.
- Do not claim physical area or depth measurement.
- Do not claim it scales to a city; that is untested.
- Do not quote a total test count as proof of accuracy.

---

## 15. Demo dataset in one paragraph

A separate demo organization holds 5 roads, 11 segments, 27 inspections, 46 detections, 25 damage
records (24 from the model, 1 manual), 15 maintenance jobs, 9 repair verifications and 2
recurrences. **Real:** the RDD2022 input photos, the model's detections and confidences, and
every calculation and verification result. **Constructed:** the after-repair images (edited
copies, captioned as such). **Synthetic:** the organization, users, contractors, road geometry,
coordinates, capture dates, traffic values, and the scripted review decisions. It was created by
a seed script that drives the real API, and a cleanup script removes only that organization.

---

## 16. One-page cheat sheet

| | |
|---|---|
| **Project** | RoadSense: Road Intelligence and Pothole Management Platform |
| **Problem** | Defects found late, repairs unverified, damage returns unnoticed |
| **Solution** | One traceable lifecycle from field capture to recurrence monitoring |
| **Lifecycle** | Capture → detect → review → map → health → estimate → priority → repair → verify → human sign-off → recurrence |
| **Stack** | Kotlin/Compose Android · Next.js/React/TypeScript · FastAPI · PostgreSQL 16 + PostGIS 3.4 · Redis + Celery · YOLO11s, PyTorch, OpenCV · Docker Compose |
| **AI model** | YOLO11s, `rdd2022-india-yolo11s` `india-v1`, threshold 0.218 |
| **Dataset** | RDD2022 India; 6,164 / 770 / 772 images; D00, D10, D20 → CRACK, D40 → POTHOLE |
| **Metrics** | mAP50 0.33 · precision 0.41 · recall 0.30 · pothole mAP50 0.41 · D10 ≈ 0 |
| **Rules** | Severity (box size + class) · Health (100 minus capped deductions) · Priority (additive, max 100) · Estimate (`rules-v2`) |
| **Health bands** | ≥ 80 GOOD · ≥ 60 FAIR · ≥ 40 POOR · < 40 CRITICAL |
| **GIS** | Points and lines in PostGIS; 5 m grouping and recurrence radius; Leaflet map |
| **Verification** | ORB + RANSAC alignment, YOLO on both images, SSIM/difference/edges → SUCCESSFUL / SUBSTANDARD / UNRESOLVED, then human review |
| **Android** | CameraX, GPS, Room, WorkManager, offline queue, signed uploads |
| **Web** | 11 modules: dashboard, roads, inspections, damage, priorities, maintenance, repairs, recurrence, map, reports, audit |
| **Security** | JWT 60 min + hashed refresh tokens · bcrypt 12 rounds · per-organization isolation · signed expiring URLs · 30 login / 300 general requests per minute · audit log |
| **Testing** | API 192 · AI worker 51 · web 16 · typecheck, lint, Ruff clean · production build passes |
| **Innovation** | Repair verification with human sign-off, recurrence detection, explainable scoring, honest provenance labels |
| **Limitations** | Modest model, not Pune-validated · verification untested on real repairs · estimate is rules · one role · not deployed · no load test |
| **Future** | Pune data and retraining · real repair validation · trained deterioration model · roles · HTTPS deployment |
