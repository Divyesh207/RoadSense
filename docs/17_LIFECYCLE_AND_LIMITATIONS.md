# 17 — Implemented Lifecycle, Methods and Limitations

This document describes what the platform actually does today, how each stage works and
what has (and has not) been validated. It supersedes target-design statements in the
earlier specifications where they differ.

## 1. Lifecycle

```
Road → Segment → Inspection → Media upload (signed URL) → AI processing (Celery)
→ Damage detection (trained YOLO11s) → Damage review → GPS grouping → Road health
→ Deterioration estimate → Priority → Maintenance job → Assignment → Repair evidence upload
→ Automated image verification → Human review → Resolution → Recurrence monitoring
→ Historical road intelligence
```

Every record stays linked: detection → damage observation → damage record → maintenance
link → job → evidence → verification (automated row + human review row) → recurrence record
(historical damage, its job and its final verification). The road detail page
(`/roads/{id}`, API `GET /roads/{id}/intelligence`) shows this history as a timeline.

| Stage | Where | Method |
|---|---|---|
| Upload | API `inspections/*/media/upload-url`, `complete` | Signed URLs; object existence checked on completion; service credentials stay server-side |
| Detection | AI worker `tasks.process_inspection` | YOLO11s `rdd2022-india-yolo11s` / `india-v1`, confidence threshold 0.218 (validation-selected) |
| Severity | AI worker | Rule-based: class + bounding-box share of the image |
| Grouping | API `damage_grouping.py` | Same damage type, open record, PostGIS `ST_DWithin` on geography within `DAMAGE_GROUPING_RADIUS_METERS` (default 5 m); detections from the same photo are never merged |
| Health | API `health_engine.py` (`health-v1.1.0`) | 100 − capped severity deductions (× documented traffic multiplier) − recurrence deduction; recalculated automatically; snapshots kept (duplicates skipped) |
| Estimate | API `prediction_engine.py` (`rules-v2`) | See §4 |
| Priority | API `priority_engine.py` (`priority-v2.1.0`) | See §5 |
| Repair verification | AI worker `tasks.verify_repair` (`repair-cv-v1.0.1`) | See §3 |
| Recurrence | API `recurrence_engine.py` (`recurrence-rules-v1.0.0`) | See §6 |

## 2. Damage detection model

- YOLO11s fine-tuned on the RDD2022 **India** subset only. Held-out RDD2022 India test split:
  mAP50 0.326, mAP50-95 0.134.
- **Supported classes:** CRACK (RDD D00 longitudinal, D10 transverse, D20 alligator) and
  POTHOLE (D40). Transverse cracks are effectively undetected in testing.
- **Unsupported:** depressions/rutting, waterlogging, ravelling/surface damage, patches.
- Scores are uncalibrated model confidences, not probabilities.
- Not validated on Pune roads or any other city; expect misses on low-contrast potholes (some
  RDD test images with labelled potholes produce no detection above 0.218).
- With `AI_REQUIRE_TRAINED_MODEL=true` the OpenCV heuristic fallback is disabled; if the
  weights cannot be loaded, jobs fail with `MODEL_UNAVAILABLE` instead of producing detections.

## 3. Repair verification

Input: a BEFORE image (latest BEFORE_REPAIR evidence, otherwise the original inspection photo
of the linked damage) and the latest AFTER_REPAIR image. Processing runs on the AI worker,
idempotent per image pair, with retries for transient storage errors.

1. Decode and quality checks (minimum size, exposure, Laplacian sharpness at native resolution).
2. ORB features, Lowe ratio matching, RANSAC homography AFTER → BEFORE with sanity checks
   (inliers, inlier ratio, scale, perspective, overlap).
3. The trained detector runs on both images at its configured threshold; BEFORE detections
   define the documented damage regions.
4. Inside those regions vs. the rest of the overlap: SSIM, standardised absolute difference,
   Canny edge density.
5. Rules: residual detection overlapping a documented region → **SUBSTANDARD**; region changed
   (change contrast ≥ 1.5 and region SSIM ≥ 0.10 below surroundings) with no residual damage →
   **SUCCESSFUL**; everything else (decode/quality failure, too few features, failed alignment,
   no damage detected in BEFORE, unchanged region, scene too different) → **UNRESOLVED**.

No verification probability or confidence is produced. The automated result never changes
the job; a reviewer confirms, rejects (with a different outcome and notes) or marks it
unresolved. The review is stored as a separate row with reviewer, time, previous/final
result, notes and model/version; the automated row is never modified.

**Limitations.** Only constructed (synthetic) image pairs have been used: procedural test
images in automated tests and inpainted copies of RDD photos in live checks. **No real
before/after repair photographs have been evaluated, so real-world accuracy is unknown.**
All damage detected in the BEFORE photo is treated as documented, not only the damage linked
to the job.

## 4. Deterioration estimate (rule-based)

There is not enough outcome history to train a regressor: the API reports
`ml_training_readiness` (segments with at least two scored health snapshots ≥ 30 days apart;
30 such segments required). Until then the estimate is explicitly `RULE_BASED_ESTIMATE`:

- Features (stored records only; unknown values stay null): current health, observed health
  trend (least-squares slope over scored snapshots spanning ≥ 7 days in the last year),
  active damage by severity, density, repeat observations, active and escalated recurrences,
  days since last inspection, inspections in the last year, days since last repair, last
  repair verification result, documented traffic class.
- Risk 0–100 = sum of itemised hand-weighted contributions × horizon factor, with a risk band.
- A future health value is produced **only** when an observed trend exists (linear
  extrapolation, labelled as such); otherwise it is null.
- No confidence or uncertainty interval. No weather data (no configured source). No pavement
  data (not modelled).

## 5. Maintenance priority

Automatic (AUTO) score = severity base + repeat sightings + active recurrences + prior verified
repairs + road-health deficit + recurrence escalation (5/10) + 0.1 × rule-based estimate risk
(if generated in the last 30 days, max 10), capped at 100; the level is never below the most
severe linked damage. Traffic is already inside the health score and is reported as an input
only. Every input and component is stored in `priority_factors` and shown on the priority
dashboard (`/priorities`). Manually set priorities are never overwritten.

## 6. Recurrence and escalation

When a damage record becomes CONFIRMED it is compared with earlier damage of the same type
within the grouping radius on the same segment that was actually repaired (status REPAIRED or
its job reached COMPLETED). Matches create POTENTIAL recurrence records with the rule inputs
(distance, days since repair, previous verification result and source, recurrence number).
Escalation (audited, reasons stored): repeated recurrence (2nd → ELEVATED, 3rd+ → CRITICAL),
previous repair SUBSTANDARD or never verified SUCCESSFUL, recurrence within 90 days, HIGH /
CRITICAL severity. Rejecting the new damage dismisses its potential recurrences (kept).

## 7. GPS and data limitations

- Phone GPS error is typically 3–10 m; the 5 m grouping radius absorbs normal drift but two
  distinct defects closer than 5 m and of the same type can be merged (different photos only).
- Damage without a segment does not affect the score of a road that has segments.
- Traffic is used only when a documented class is entered for the road; it is never estimated.
- Signed URLs use `PUBLIC_API_BASE_URL`; when it is a LAN address for phone testing, browsers
  and scripts must be able to reach that address.

## 8. Validation status

| What | Evidence | Meaning |
|---|---|---|
| Software lifecycle | API/worker/PostGIS suites; live E2E `services/api/tests_e2e` on the Docker stack | Records are created, linked and updated correctly through the whole lifecycle |
| Detection accuracy | RDD2022 India held-out split metrics only | Real-world accuracy on target roads unknown |
| Repair verification accuracy | None on real data | Requires collecting real before/after repair pairs |
| Deterioration estimate accuracy | None | Rule-based; no outcomes to evaluate against yet |

Running the live E2E (creates and deletes its own road; audit entries are kept):

```
E2E_API_URL=http://localhost:8000/api/v1 E2E_EMAIL=... E2E_PASSWORD=... \
E2E_IMAGE=path/to/road_photo_with_potholes.jpg \
E2E_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/road_platform \
E2E_DOCKER_CLEANUP=1 pytest services/api/tests_e2e -s
```

## 9. Readiness

Suitable for an academic demonstration and controlled pilot data collection. Not production
ready: no TLS, secret management or monitoring; detection not validated on target roads;
repair verification and deterioration estimates not validated on real outcomes. Data needed
next: real before/after repair photo pairs, repeated inspections of the same segments over
months (to enable a trained deterioration model), and documented traffic counts.
