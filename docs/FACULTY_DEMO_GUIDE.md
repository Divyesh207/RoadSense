# RoadSense faculty demo guide

A dedicated **DEMO / SYNTHETIC** dataset that shows the whole RoadSense lifecycle end to end:
inspection, AI detection, human review, road health, rule-based estimates, priorities,
maintenance, repair verification, recurrence, reports and audit.

## Commands

Start the stack first (`docker compose up -d`), then from the repository root:

**Seed the demo dataset** (about 3 minutes; safe to run again):

```powershell
.\.venv\Scripts\python.exe scripts\seed_faculty_demo.py
```

**Remove the demo dataset** (only the demo dataset; asks before deleting):

```powershell
.\.venv\Scripts\python.exe scripts\cleanup_faculty_demo.py
```

Add `--yes` to skip the question, or `--dry-run` to only see what would be removed.

**Login for the demo:** open `http://localhost:3000/login`. The demo accounts and their
password are written to `scripts\demo\faculty_demo.local.env` (local, git-ignored) the first
time you seed. Use the supervisor account for the presentation.

| Account | Used by the seed for |
|---|---|
| `supervisor@faculty-demo.roadsense.example` | roads, health, estimates, reports |
| `inspector@faculty-demo.roadsense.example` | inspections and photo uploads |
| `reviewer@faculty-demo.roadsense.example` | damage reviews, repair-verification reviews, recurrence reviews |
| `engineer@faculty-demo.roadsense.example` | maintenance jobs and repair evidence |

## 1. What the dataset contains

Everything lives in its own organization, **"DEMO - RoadSense Faculty Demo Authority
(SYNTHETIC)"** (code `FACULTY-DEMO`). Your other organization's data is not touched and is not
visible while you are signed in to the demo organization.

| Item | Count |
|---|---|
| Roads / segments | 5 / 11 |
| Field inspections | 27 (22 with detections, 5 with none: 4 clean roads and 1 clean follow-up) |
| AI detections (trained YOLO11s) | 46 |
| Damage records | 25 (24 from AI detections, 1 entered by a person) |
| Human damage reviews | 21 (19 confirmed, 2 rejected); 3 records left awaiting review |
| Maintenance jobs | 15 |
| Repair evidence images | 10 (1 BEFORE, 9 AFTER) |
| Repair verifications | 9 automated, 7 human reviews |
| Recurrence records | 2 |
| Reports | 5 |
| Contractors | 3 |

Roads: DEMO - Akurdi Main Road (3 segments), DEMO - Akurdi Station Road, DEMO - Akurdi
Internal Road, DEMO - Akurdi College Road, DEMO - Pune Demo Connector (2 segments each).

Contractors: DEMO - Pune Roadworks Team, DEMO - Akurdi Maintenance Unit, DEMO - Road Repair
Contractor A.

## 2. What is synthetic, and what is real

Say this plainly in the demonstration.

**Synthetic / scripted (by the seed):**

- The organization, users and contractors are demo accounts.
- The road and segment lines are drawn for the demo around Akurdi and Pune. They do not trace
  surveyed roads, and the coordinates are not real observation points.
- Inspection capture dates are demo dates spread over the last four months.
- Traffic figures are demo values, labelled as such in the road record.
- Review decisions, reviewer-chosen severities and maintenance notes are scripted decisions.
- The AFTER-repair images are **edited copies of the BEFORE photos** (damage area filled and
  covered with a patch, or left partly or wholly unrepaired). Each one carries a burned-in
  caption saying it is a constructed demo image. They are not photographs of real repairs.

**Third-party photographs:**

- The inspection photos are official **test images of the RDD2022 India dataset** (Arya et
  al. 2022, DOI 10.6084/m9.figshare.21431547, CC BY-SA 4.0). They are real road photographs,
  but they were **not taken in Akurdi or at the demo coordinates**. The test images were not
  used to train or evaluate the model.

**Produced by the platform itself, not by the seed:**

- AI detections, classes and confidences (model `rdd2022-india-yolo11s`, version `india-v1`,
  at its deployed threshold 0.218).
- Rule-based severity, road health scores, deterioration estimates and maintenance priorities.
- Every automated repair-verification result (algorithm `repair-cv-v1.0.1`).
- GPS grouping of repeat sightings, recurrence matches and escalations.
- Dashboard numbers, reports and audit entries.

The photos used for each scenario were chosen by first running the real detector and the
real verification code over a pool of 160 test images. That selection decides *which photo*
illustrates each outcome; it does not set any result.

## 3. Expected dashboard

After a fresh seed, signed in as the demo supervisor:

| Tile | Value |
|---|---|
| Roads / segments | 5 / 11 |
| Active damage | 17 (3 awaiting review) |
| Critical / high (active) | 3 / 4 |
| Average road health | 79.3 |
| Maintenance jobs | 15 (2 open, 2 in progress) |
| Repairs pending verification | 3 |
| Verified repairs | 3 |
| Active recurrences | 2 (2 escalated) |

Charts: jobs by status (OPEN 2, ASSIGNED 1, IN_PROGRESS 2, COMPLETED 1, VERIFICATION_PENDING 3,
VERIFIED 3, REJECTED 2, CANCELLED 1); road health (GOOD 3, FAIR 2); damage by severity
(CRITICAL 3, HIGH 6, MEDIUM 12, LOW 4); final verification outcomes (SUCCESSFUL 4,
SUBSTANDARD 3, UNRESOLVED 2).

Road health by segment ranges from 97.5 (GOOD) to 48.0 (POOR). No segment reaches the
platform's CRITICAL health band; that is what the health rules produce for this data.
Deterioration estimates range from 2.4 (LOW) to 55.8 (HIGH); all are rule-based.

## 4. The repair-verification scenarios

Open **Repairs & Verification**. Each row is a real run of the verification pipeline.

| Job | AFTER image | Automated result | Human review | Job ends as |
|---|---|---|---|---|
| Pothole repair, Akurdi Main Road seg 1 | fully patched | SUCCESSFUL | confirmed | VERIFIED |
| Pothole repair, Akurdi Main Road seg 2 | partly patched | SUBSTANDARD (residual damage detected) | confirmed | REJECTED |
| Pothole repair, Akurdi Station Road seg 1 | unchanged | SUBSTANDARD (residual damage detected) | confirmed | back to IN_PROGRESS (rework) |
| Crack sealing, Akurdi Station Road seg 2 | fully sealed | SUCCESSFUL | **awaiting review** | VERIFICATION_PENDING |
| Crack sealing, Akurdi Internal Road seg 1 | unchanged | UNRESOLVED (region unchanged) | marked unresolved | VERIFICATION_PENDING |
| Crack sealing, Akurdi Internal Road seg 2 | photo of a different place | UNRESOLVED (alignment failed) | **awaiting review** | VERIFICATION_PENDING |
| Pothole repair, Pune Demo Connector seg 1 | fully patched | SUCCESSFUL | confirmed | VERIFIED |
| Crack sealing, Akurdi College Road seg 1 | fully sealed | SUCCESSFUL | **rejected by the reviewer** (final SUBSTANDARD) | REJECTED |
| Crack sealing, Akurdi College Road seg 2 | fully sealed | SUCCESSFUL | confirmed | VERIFIED |

Points worth making:

- An unrepaired pothole comes out as SUBSTANDARD, not UNRESOLVED, because the detector still
  finds the damage. UNRESOLVED means the evidence cannot support a decision.
- The College Road seg 1 row shows that the automated result and the human decision are
  separate: the reviewer overrode a SUCCESSFUL analysis.
- The automated result never changes the job by itself; the human review does.

## 5. The recurrence scenarios

Open **Recurrence**.

- **Akurdi Main Road seg 1:** pothole repaired and verified, then a later inspection finds a
  pothole 1 m away. The platform records a recurrence and escalates it to CRITICAL (early
  recurrence plus critical severity). A reviewer confirmed it, and a new job "Re-repair after
  recurrence" is open with priority CRITICAL.
- **Pune Demo Connector seg 1:** same pattern, escalation ELEVATED, still awaiting review.
- **Akurdi College Road seg 2:** repaired, and the follow-up inspection finds nothing. No
  recurrence.

## 6. Five-minute demo flow

1. **Dashboard** - the tiles in section 3. Say that every number is counted from records.
2. **Spatial Map** - 25 damage points, 11 segments coloured by health, 27 inspection points.
   Click a red marker on Akurdi Main Road; show type, severity, model confidence, coordinates.
   Filter by severity CRITICAL, then reset.
3. **Roads & Segments** - open "DEMO - Akurdi Main Road". Show health per segment
   (65 FAIR, 82 GOOD, 52 POOR), the deductions, and the timeline of events.
4. **Damage Intelligence** - 25 records. Point out "Trained model" with its confidence, the
   one "Manual entry", the 3 awaiting review and the 2 rejected as false positives.
5. **Priorities** - rank 1 is "Urgent pothole repair, Akurdi Main Road seg 3" at 100. Show the
   component breakdown and the label "rule-based, not a trained model".
6. **Maintenance Operations** - the board with jobs in every state. Open "DEMO - Pothole
   repair, Akurdi Main Road seg 1": contractor, status history, linked damage.
7. **Repairs & Verification** - on that same job, show the BEFORE and AFTER images and the
   automated findings, then the reviewer's decision. Then show the College Road seg 1 row
   where the reviewer disagreed.
8. **Recurrence** - the two records in section 5 and the rules that fired.
9. **Reports & Exports** - download the Executive Road Condition PDF.
10. **Audit & Security** - who confirmed which damage and who reviewed which verification.

For the full lifecycle on one record, follow Akurdi Main Road seg 1 through steps 2 to 8:
inspection, detection, review, job, repair evidence, verification, human review, recurrence,
re-repair job.

## 7. Before the demonstration

- Start Docker and run `docker compose ps`; `road_platform_api` must be healthy.
- Run the seed command once. It takes about 3 minutes on an empty demo organization and
  about 25 seconds when everything already exists.
- Open a maintenance job with evidence and check the BEFORE/AFTER images load. Image links
  use the server's `PUBLIC_API_BASE_URL` (currently this laptop's Wi-Fi address). If the
  laptop is on a different network in the demo room, the images will not load until that
  setting matches the laptop's address.
- The first seed downloads 27 photos (about 20 MB transferred) from the public RDD2022
  archive, so it needs internet once. Later runs use the copies in `scripts\demo\photos`.

## 8. Known limitations

- **Timestamps.** Only inspection capture dates are spread over time. Damage, maintenance,
  verification, health and audit timestamps are the real time the seed ran, so recurrences
  show "0 days since repair" and health trends cover minutes, not months.
- **Photos are not from the demo locations.** See section 2.
- **AFTER images are constructed.** The verification results are genuine pipeline output, but
  on edited images. The pipeline has not been validated on photographs of real repairs.
- **Model accuracy.** On its held-out test split the model's recorded mAP50 is 0.33. The demo
  photos were chosen because the model detects damage in them; of the 160 screened test
  photos it reported nothing in 102, which cannot be checked for misses because the test
  images have no labels.
- **Only POTHOLE and CRACK** are covered, which is what the model's class mapping supports.
- **Health bands.** The data produces GOOD, FAIR and POOR segments, not CRITICAL.
- **Estimates are rule-based.** There is no trained deterioration model.
- **Roles.** The platform has only the ADMINISTRATOR role configured, so all four demo
  accounts are administrators.
- **Demo contractors are visible to other organizations** in the assignee list, because
  contractor organizations are shared. Cleanup removes them.
- **Audit log** records damage confirmations and rejections, verification reviews and
  recurrence escalations. Maintenance status changes are in each job's status history instead.
- **Inspection source** reads "API": the seed uses the same upload API as the field app, not
  a phone. The Android app and its `http://127.0.0.1:8000/` configuration are unchanged.
- **Inspections page counters** show 0 under "Completed" although all 27 are ANALYZED; the
  list itself is correct.

## 9. Files

| File | Purpose |
|---|---|
| `scripts/seed_faculty_demo.py` | Seeds the dataset through the API |
| `scripts/cleanup_faculty_demo.py` | Removes only the demo dataset |
| `scripts/demo/demo_plan.py` | The dataset as data: roads, sites, scenarios |
| `scripts/demo/repair_derivatives.py` | Builds the constructed AFTER images |
| `scripts/demo/fetch_demo_photos.py` | Downloads the RDD2022 photos |
| `scripts/demo/photos/` | Downloaded photos (git-ignored) |
| `scripts/demo/faculty_demo.local.env` | Demo logins (git-ignored) |
| `scripts/demo/last_seed_summary.json` | Result of the last seed (git-ignored) |
