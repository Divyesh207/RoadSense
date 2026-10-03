# 08 — AI/ML SPECIFICATION

**Project:** Road Intelligence & Pothole Management Platform  
**Document:** AI/ML Specification  
**Version:** 1.0  
**Status:** Approved Technical Specification  
**Parent Documents:** `01_PROJECT_CONTEXT.md`, `02_PRD.md`, `03_SRS.md`, `04_SYSTEM_ARCHITECTURE.md`, `05_TECH_STACK.md`, `06_DATABASE_SCHEMA.md`, `07_API_SPECIFICATION.md`

> **Implementation status (current code):** this document is the *target* design.
> - **Trained detector:** YOLO11s fine-tuned on RDD2022 India (`rdd2022-india-yolo11s` / `india-v1`),
>   trained on D00/D10/D20 (cracks → CRACK) and D40 (potholes → POTHOLE). Its scores are uncalibrated
>   model confidence, not probabilities.
> - **Unsupported classes:** the model does not detect DEPRESSION, WATERLOGGING, SURFACE_DAMAGE or OTHER.
> - **Metrics vs generalization:** held-out RDD2022 India test split mAP50 0.326 / mAP50-95 0.134. These
>   are not a measure of accuracy on Pune roads or other cities and cameras.
> - **Heuristic fallback:** the deterministic OpenCV heuristic (`OPENCV_HEURISTIC` / `HEURISTIC_FALLBACK`)
>   is used only when no trained weights are configured and is labelled as rule-based.
> - Deterioration prediction is a hand-weighted rule set (`Rule-Based-Deterioration-Estimate`), not
>   XGBoost, and reports no confidence or uncertainty. Repair verification checks evidence presence and
>   GPS distance only; no before/after image comparison is implemented yet. See README section 4.

---

## 1. Purpose

This document defines the artificial intelligence and machine learning architecture of the Road Intelligence & Pothole Management Platform.

The AI/ML subsystem is responsible for:

1. Detecting road damage from images and video.
2. Classifying detected damage.
3. Estimating damage severity.
4. Associating detections with geographic locations and road segments.
5. Generating road-condition intelligence.
6. Predicting deterioration using historical road data.
7. Verifying completed repairs using post-repair evidence.
8. Providing measurable and auditable AI outputs.
9. Feeding verified historical information back into the road intelligence lifecycle.

The AI system is a **decision-support system**, not an autonomous authority for maintenance decisions.

Human review remains mandatory for important operational decisions.

---

# 2. AI/ML Principles

The AI subsystem follows these principles:

### 2.1 Local AI First

Core AI functionality must run using locally deployed models.

The system must not require:

- OpenAI APIs
- Gemini APIs
- Claude APIs
- External generative AI services
- Cloud AI inference APIs

for core detection, prediction, severity assessment, or repair verification.

---

### 2.2 Explainability

AI outputs must contain enough information to understand why an output was generated.

Examples:

- Detection → class + confidence + bounding box.
- Severity → contributing measurable factors.
- Prediction → feature set/version + model version.
- Repair verification → evidence + verification result + confidence.

---

### 2.3 Human-in-the-Loop

AI recommendations are not automatically treated as ground truth.

The workflow is:

```text
AI Detection
      ↓
AI Classification
      ↓
Severity Estimate
      ↓
Human Review
      ↓
Confirmed / Edited / Rejected
```

Original AI output must always be preserved.

---

### 2.4 Reproducibility

Every AI result must be traceable to:

- model version
- dataset version where applicable
- feature version where applicable
- preprocessing version
- processing run
- inference timestamp
- relevant input media
- runtime/device information where useful

---

### 2.5 Historical Preservation

AI results must not silently overwrite historical results.

When a model changes:

```text
Old Model Result
        +
New Model Result
        +
Model Versions
        ↓
Historical AI Record
```

remain traceable.

---

# 3. AI/ML Architecture

The AI subsystem follows this pipeline:

```text
Inspection Media
      ↓
Media Validation
      ↓
Preprocessing
      ↓
YOLO Detection
      ↓
Postprocessing / NMS
      ↓
Damage Classification
      ↓
Severity Assessment
      ↓
Geospatial Association
      ↓
Canonical Damage Record
      ↓
Road Health Features
      ↓
Deterioration Prediction
      ↓
Maintenance Intelligence
      ↓
Repair Evidence
      ↓
Repair Verification
      ↓
Recurrence Feedback
```

---

# 4. AI Components

The initial AI stack consists of:

| Component | Technology |
|---|---|
| Object Detection | YOLO + PyTorch |
| Image Processing | OpenCV |
| Numerical Processing | NumPy |
| Data Processing | Pandas |
| Classical ML | scikit-learn |
| Deterioration Prediction | XGBoost |
| Media Processing | FFmpeg |
| Model Artifacts | Object Storage |
| AI Execution | Celery Worker |
| Database | PostgreSQL + PostGIS |

---

# 5. AI Worker Architecture

AI workloads execute asynchronously.

```text
FastAPI
   ↓
Redis
   ↓
Celery Job
   ↓
AI Worker
   ├── Media Preprocessor
   ├── YOLO Detector
   ├── Severity Engine
   ├── Geospatial Processor
   ├── Prediction Engine
   └── Repair Verification Engine
   ↓
PostgreSQL / Supabase Storage
```

The API must not block while long-running AI inference is executing.

---

# 6. Processing Job Lifecycle

AI jobs use the following states:

```text
QUEUED
  ↓
RUNNING
  ↓
COMPLETED
```

Failure:

```text
RUNNING
  ↓
FAILED
```

Cancellation:

```text
QUEUED/RUNNING
  ↓
CANCELLED
```

Each job must contain sufficient metadata to diagnose failures.

---

# 7. Media Input

Supported initial inputs:

- JPEG
- PNG
- MP4
- other formats explicitly enabled by configuration

Media is uploaded to Supabase Storage.

PostgreSQL stores metadata rather than large binary media.

Example:

```text
inspection-media/
    organization/
        inspection/
            image-001.jpg
            video-001.mp4
```

---

# 8. Media Validation

Before AI inference, the worker must validate:

- file existence
- MIME type
- file size
- image/video readability
- dimensions
- corruption
- supported format
- frame availability for video
- metadata where available

Invalid media must produce an explicit processing error.

The system must never silently process corrupt or unsupported media.

---

# 9. Image Preprocessing

OpenCV is used for preprocessing.

Possible operations include:

- decoding
- resizing
- normalization
- color-space conversion
- brightness handling
- contrast adjustment
- frame extraction
- image quality checks

Preprocessing must be deterministic where practical.

The preprocessing version must be recorded when it materially affects inference.

---

# 10. YOLO Detection Pipeline

The primary detection pipeline is:

```text
Input Image
     ↓
Preprocessing
     ↓
YOLO Model
     ↓
Raw Predictions
     ↓
Confidence Filtering
     ↓
Non-Maximum Suppression
     ↓
Duplicate Suppression
     ↓
Validated Detections
```

Each detection must contain at minimum:

- detection ID
- inspection ID
- media ID
- class
- confidence
- bounding box
- location where available
- model ID/version
- processing run ID
- timestamp

---

# 11. Initial Damage Classes

The initial supported classes are:

```text
POTHOLE
CRACK
DEPRESSION
WATERLOGGING
SURFACE_DAMAGE
OTHER
```

The class system must be extensible.

### OTHER Rule

`OTHER` is an explicit fallback class.

It must not be used to hide:

- low confidence
- unknown model behavior
- missing labels
- annotation mistakes
- unsupported conditions that should instead be reviewed

Low-confidence detections should remain identifiable as uncertain.

---

# 12. Detection Confidence

Each detection produces a confidence score.

Conceptually:

```text
0.0 ≤ confidence ≤ 1.0
```

Confidence thresholds must be configurable.

The system should support configurable policies such as:

```text
High Confidence
Medium Confidence
Low Confidence
```

Exact production thresholds must be determined through validation data rather than arbitrarily hard-coded.

The threshold configuration must be versioned where required for reproducibility.

---

# 13. Non-Maximum Suppression

YOLO predictions can produce overlapping detections for the same physical damage.

NMS must be used to reduce duplicate detections.

Conceptually:

```text
Multiple overlapping boxes
          ↓
IoU comparison
          ↓
Highest-confidence candidate retained
          ↓
Overlapping duplicates suppressed
```

The IoU threshold must remain configurable.

For video processing, temporal duplicate handling may additionally be required.

---

# 14. Video Processing

Video processing follows:

```text
Video
 ↓
Metadata Extraction
 ↓
Frame Sampling
 ↓
Frame Preprocessing
 ↓
YOLO Detection
 ↓
Temporal Duplicate Handling
 ↓
GPS Synchronization
 ↓
Detection Aggregation
 ↓
Canonical Damage Records
```

The system should not necessarily run inference on every frame.

Configurable frame sampling may be used to control:

- processing cost
- latency
- duplicate detections
- storage requirements

For each video detection, the system should preserve:

- frame number where applicable
- video timestamp
- media ID
- GPS information where available
- model version

---

# 15. Detection Aggregation

The same physical damage may appear across multiple video frames.

The system must avoid creating multiple canonical damage records for the same physical event solely because it appears in consecutive frames.

Possible aggregation signals include:

- geographic distance
- bounding-box overlap
- temporal proximity
- class similarity
- confidence
- road-segment association

The aggregation algorithm must be deterministic and versioned.

---

# 16. Geospatial Association

AI detections must be connected to real-world road locations.

Primary source:

```text
Inspection GPS
+
Media GPS
+
Frame GPS where available
```

The system then uses PostGIS to associate the detection with:

```text
Road
   ↓
Road Segment
```

Conceptually:

```text
Detection Point
      ↓
Nearest / containing road geometry
      ↓
Road Segment
```

The matching tolerance must be configurable.

If the association is uncertain, the system must mark the association as uncertain rather than silently assigning an incorrect road.

---

# 17. Damage Record Creation

Raw AI detections and canonical damage records are different concepts.

```text
AI Detection
     ↓
Review / Validation
     ↓
Damage Record
```

`ai_detections` stores model output.

`damage_records` stores the canonical operational representation.

This separation allows:

- reprocessing
- model comparison
- human correction
- auditability
- historical preservation

---

# 18. Human Review

The review workflow is:

```text
AI Detection
     ↓
REVIEW_REQUIRED
     ↓
Reviewer
 ┌───┼────┐
 ↓   ↓    ↓
Confirm Edit Reject
```

The reviewer may modify:

- class
- location
- severity
- damage validity
- notes

The original AI result must remain unchanged.

The review record must contain:

- reviewer
- timestamp
- previous state
- new state
- review action
- optional comment

---

# 19. Severity Assessment

Severity is represented using:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Severity must not be determined solely from YOLO confidence.

Confidence answers:

> How confident is the model that the detected object belongs to this class?

Severity answers:

> How significant is the physical road condition?

These are different concepts.

---

# 20. Severity Features

Initial severity assessment may consider:

### Visual factors

- detected damage area
- bounding-box dimensions
- relative size
- damage type
- estimated extent
- damage density

### Geographic factors

- road segment
- clustering
- recurrence
- proximity to other damage

### Historical factors

- previous occurrences
- unresolved damage
- repeated damage
- previous repair history

### Operational factors

- inspection context
- road classification where available
- confirmed reviewer information

Only features actually available in the system may be used.

---

# 21. Severity Engine

The severity engine should be modular.

Initial implementation may use a transparent rules/configuration layer.

Conceptually:

```text
Damage Features
      ↓
Severity Rules / Model
      ↓
LOW / MEDIUM / HIGH / CRITICAL
      ↓
Contributing Factors
```

Exact thresholds and weights must be configurable and validated using real labeled data.

The system must preserve the severity method/version used.

---

# 22. Road Health Intelligence

Road health is derived from historical and current road-condition data.

Potential inputs include:

- confirmed damage count
- severity distribution
- damage density
- unresolved damage
- recurrence
- recent inspection results
- maintenance history
- time since maintenance
- health trend

The system must generate historical:

```text
road_health_snapshots
```

rather than continuously overwriting one score.

The exact production formula must be documented and validated before being treated as an official operational metric.

---

# 23. Deterioration Prediction

The initial predictive model is:

**XGBoost**

with supporting libraries:

- scikit-learn
- Pandas
- NumPy

The prediction system estimates future deterioration based on historical road-segment data.

It is not a guarantee of future road condition.

---

# 24. Prediction Target

Before training a deterioration model, the target must be explicitly defined.

Possible target definitions include:

### Classification

Predict whether a segment will experience a deterioration event within a defined future horizon.

Example:

```text
Will HIGH/CRITICAL deterioration occur within N days?
```

### Regression

Predict a future numerical road-health value or deterioration score.

The project must select and document the target before production model training.

Training data must not contain future information unavailable at prediction time.

---

# 25. Prediction Features

Initial candidate features include:

- historical damage count
- damage density
- severity distribution
- unresolved damage count
- recurrence frequency
- inspection frequency
- inspection freshness
- health score
- health-score trend
- time since last maintenance
- previous maintenance count
- previous repair outcomes
- recent confirmed damage
- road-segment history

Weather, traffic, road age, traffic load, or other external variables must not be used unless the corresponding data source has actually been integrated and validated.

---

# 26. Temporal Leakage Prevention

Deterioration prediction is historical/time-dependent.

Randomly splitting records can cause data leakage when the same road segment appears in both training and test data across related time periods.

Therefore, dataset splitting should consider:

- time
- road segment
- organization where appropriate

The exact split strategy must be recorded with the model.

---

# 27. Prediction Output

Each prediction should contain:

- road segment ID
- prediction type
- prediction value/class
- prediction horizon
- model ID/version
- feature version
- prediction timestamp
- input snapshot/reference
- uncertainty/confidence where supported
- status

Predictions are historical records.

A new prediction must not silently overwrite previous predictions.

---

# 28. Model Registry

The database contains the `ai_models` entity.

Models should have lifecycle states such as:

```text
DRAFT
VALIDATED
APPROVED
DEPLOYED
RETIRED
```

A model record should identify:

- model name
- model type
- version
- artifact location
- checksum where applicable
- framework/version
- dataset version
- preprocessing version
- feature version
- validation metrics
- creation timestamp
- deployment status

---

# 29. Model Lifecycle

The standard lifecycle is:

```text
Data Collection
      ↓
Annotation
      ↓
Dataset Version
      ↓
Train / Validate / Test
      ↓
Evaluation
      ↓
Model Registration
      ↓
Approval
      ↓
Deployment
      ↓
Inference
      ↓
Monitoring
      ↓
Retraining
      ↓
Replacement / Retirement
```

A deployed model must always have a unique identifiable version.

---

# 30. Dataset Management

Datasets must be versioned.

Example:

```text
road-damage-v1
road-damage-v2
road-damage-v3
```

Each version should record:

- source
- collection period
- annotation version
- class definitions
- train/validation/test composition
- preprocessing
- exclusions
- class distribution
- known limitations

---

# 31. Detection Annotation Format

The initial YOLO dataset format may use:

```text
class_id center_x center_y width height
```

with normalized coordinates.

Example:

```text
0 0.512 0.476 0.221 0.184
```

Class IDs must map to the canonical damage-class registry.

The mapping must not be duplicated independently across different services.

---

# 32. Dataset Quality

Training data should be reviewed for:

- incorrect labels
- duplicate images
- corrupted media
- poor visibility
- extreme class imbalance
- inconsistent annotations
- location leakage
- train/test contamination

Low-quality samples should be documented rather than silently removed.

---

# 33. Class Imbalance

The system must monitor class distribution.

If classes are heavily imbalanced, the training process may use appropriate techniques such as:

- targeted data collection
- augmentation
- sampling strategies
- class-aware evaluation

The chosen strategy must be documented with the model version.

---

# 34. Data Augmentation

Image augmentation may be used during training.

Potential augmentations:

- brightness variation
- contrast variation
- scaling
- cropping
- horizontal transformations where semantically valid
- blur/noise simulation
- weather/lighting simulation where representative

Augmentation must not create unrealistic road conditions or invalid labels.

---

# 35. Detection Evaluation

Detection models must be evaluated using:

- precision
- recall
- per-class AP
- mAP@0.5
- mAP@0.5:0.95
- confusion/error analysis

Metrics must be reported for:

- overall model
- each damage class
- relevant environmental conditions where data permits

A model must not be considered production-ready solely because one aggregate metric is high.

---

# 36. Severity Evaluation

For categorical severity:

- accuracy
- precision
- recall
- macro F1
- confusion matrix
- per-class performance

If an ordinal formulation is introduced later, suitable ordinal/regression metrics may also be added.

Human-reviewed severity labels should form the evaluation reference set.

---

# 37. Deterioration Model Evaluation

Evaluation depends on the selected target.

### Classification

Possible metrics:

- precision
- recall
- F1
- ROC-AUC
- PR-AUC
- calibration metrics when probabilities are used

### Regression

Possible metrics:

- MAE
- RMSE
- R²

Evaluation must use a time-aware and leakage-resistant test set.

---

# 38. Repair Verification

Repair verification compares pre-repair and post-repair evidence.

Conceptually:

```text
Before Repair
      +
Repair Evidence
      ↓
AI Verification
      ↓
Verification Result
```

Possible outputs:

```text
VERIFIED
PARTIALLY_VERIFIED
FAILED
REVIEW_REQUIRED
```

The final operational status must follow the repair verification workflow defined by the application.

---

# 39. Repair Verification Features

Potential inputs include:

- before/after image
- damage location
- damage type
- original severity
- visual change
- remaining visible damage
- evidence quality
- geographic consistency
- temporal consistency

The system must not mark a repair successful solely because an image was uploaded.

---

# 40. Repair Verification Human Review

AI verification can recommend a result.

For uncertain or critical cases:

```text
AI Verification
      ↓
REVIEW_REQUIRED
      ↓
Human Reviewer
      ↓
Final Verification
```

The original AI verification output remains preserved.

---

# 41. AI Processing Run

Each inference operation must be associated with an AI processing run.

The processing run should identify:

- processing run ID
- model ID
- model version
- preprocessing version
- input reference
- execution start
- execution end
- status
- error information
- runtime/device information where useful

This connects database results with the exact execution context.

---

# 42. AI Database Integration

AI components map to the database as follows:

| AI Component | Database Entity |
|---|---|
| Model registry | `ai_models` |
| Inference execution | `ai_processing_runs` |
| Raw YOLO output | `ai_detections` |
| Canonical damage | `damage_records` |
| Human review | `damage_reviews` |
| Road condition | `road_health_snapshots` |
| Maintenance priority | `maintenance_priority_snapshots` |
| Prediction | `deterioration_predictions` |
| Repair evidence | `repair_evidence` |
| Repair verification | `repair_verifications` |
| Recurrence | `recurrence_records` |

---

# 43. Model Artifact Storage

Model artifacts must be stored outside Git.

Examples:

```text
model-artifacts/
    detection/
        road-damage-v1/
            model.pt
            metadata.json
    prediction/
        deterioration-v1/
            model.json
            metadata.json
```

The database stores the artifact reference and model metadata.

Large model files must not be committed into the application source repository.

---

# 44. Model Loading

AI workers should load approved models from configured artifact locations.

The worker should:

1. Identify the required model version.
2. Validate model metadata.
3. Load the artifact.
4. Cache it when appropriate.
5. Verify compatibility.
6. Execute inference.
7. Record the model version.

Model loading failures must result in explicit job failures.

---

# 45. CPU/GPU Support

The AI worker should support:

```text
GPU → preferred when available
CPU → fallback where practical
```

The application must not assume that every deployment has a GPU.

Inference configuration should expose device selection.

Future deployment may move the AI worker to dedicated GPU infrastructure without changing the public API contract.

---

# 46. AI Resource Controls

AI workers should enforce configurable limits for:

- maximum media size
- maximum video duration
- maximum frame count
- image dimensions
- concurrent jobs
- processing timeout
- memory usage where practical

This prevents a single upload from exhausting worker resources.

---

# 47. Idempotency

AI processing must be safe to retry.

A retry must not create duplicate canonical damage records.

Processing identity should be based on appropriate identifiers such as:

```text
inspection
+
media
+
model version
+
processing configuration
```

The exact idempotency key must align with the API and database constraints.

---

# 48. Reproducibility Metadata

Every important AI result should be reproducible from recorded metadata.

At minimum:

```text
Model Version
Dataset Version
Preprocessing Version
Feature Version
Processing Run
Input Reference
Timestamp
```

For prediction:

```text
Feature Snapshot
Prediction Target Version
Model Version
```

For verification:

```text
Evidence Reference
Verification Model Version
```

---

# 49. Explainability Requirements

### Detection

Expose:

- class
- confidence
- bounding box
- media/frame reference

### Severity

Expose:

- severity
- contributing factors
- severity method/version

### Prediction

Expose:

- prediction
- horizon
- model version
- feature version
- relevant feature values or feature snapshot

### Repair Verification

Expose:

- evidence used
- verification result
- confidence where applicable
- model version
- review status

The platform should prefer measurable explanations over opaque natural-language explanations.

---

# 50. AI Monitoring

The AI system must monitor:

### Operational metrics

- job count
- success rate
- failure rate
- queue depth
- processing latency
- throughput
- worker utilization

### Model/data metrics

- confidence distribution
- class distribution
- detection frequency
- false-positive feedback
- false-negative feedback
- human correction frequency
- input quality
- data drift indicators
- model performance on reviewed samples

---

# 51. Human Feedback Loop

Human reviews create valuable training data.

Example:

```text
AI Prediction
     ↓
Human Review
     ↓
Correction
     ↓
Validated Label
     ↓
Training Dataset
     ↓
Future Model Version
```

Corrections must not immediately retrain production models.

They first enter a controlled dataset/versioning process.

---

# 52. Retraining Policy

Retraining may be triggered by:

- sufficient new labeled data
- measurable performance degradation
- new damage classes
- environmental/domain changes
- recurring false positives
- recurring false negatives
- significant data distribution changes

Retraining must produce a new model version.

Existing production results must remain historically traceable.

---

# 53. Model Deployment Policy

A model must pass validation before deployment.

Recommended lifecycle:

```text
DRAFT
 ↓
VALIDATED
 ↓
APPROVED
 ↓
DEPLOYED
```

A deployed model can later become:

```text
RETIRED
```

Only explicitly approved versions may be used for production inference.

---

# 54. Model Rollback

The system must support model rollback.

If a newly deployed model causes unacceptable operational or technical problems:

```text
Current Model
     ↓
Disable
     ↓
Previous Approved Model
     ↓
Redeploy
```

Historical results must continue referencing the model that originally generated them.

Rollback must not rewrite historical AI records.

---

# 55. Environment Separation

AI models must be separated by environment where necessary:

```text
Development
Staging
Production
```

Production inference must not accidentally load an experimental model.

Model configuration must be environment-specific.

---

# 56. AI Security

AI-related security requirements include:

- model artifacts must not be publicly writable
- signed/controlled artifact access
- upload validation before processing
- resource limits
- authenticated processing requests
- organization isolation
- secure storage access
- no client-controlled model execution
- no arbitrary executable model loading
- audit logging for important model operations

---

# 57. Privacy and Data Handling

Inspection media may contain:

- vehicles
- people
- private property
- license plates
- geographic information

The system must follow the project's privacy requirements.

Future privacy improvements may include:

- automatic anonymization
- license-plate blurring
- face blurring
- configurable retention policies

These are separate modules unless explicitly implemented.

---

# 58. Failure Handling

AI failures must be explicit.

Examples:

```text
MODEL_NOT_FOUND
MODEL_LOAD_FAILED
UNSUPPORTED_MEDIA
MEDIA_CORRUPTED
INFERENCE_TIMEOUT
GPU_OUT_OF_MEMORY
PROCESSING_FAILED
INVALID_MODEL_VERSION
PREDICTION_FAILED
VERIFICATION_FAILED
```

The worker must record meaningful failure information without exposing sensitive internal details to clients.

---

# 59. AI API Integration

The AI subsystem is accessed through backend APIs.

Clients do not directly invoke:

- YOLO
- PyTorch
- XGBoost
- Redis
- AI model artifacts

The flow remains:

```text
Web / Android
      ↓
FastAPI
      ↓
Processing Job
      ↓
AI Worker
```

---

# 60. AI Testing Strategy

### Unit Tests

Test:

- preprocessing
- class mapping
- confidence filtering
- NMS
- severity rules
- feature generation
- prediction preprocessing
- output validation

### Integration Tests

Test:

```text
Upload
→ Job
→ Worker
→ AI Output
→ Database
```

### Model Tests

Validate:

- expected input shape
- output schema
- class mapping
- model artifact integrity
- version metadata

### Regression Tests

Maintain representative evaluation datasets to detect performance regressions between model versions.

---

# 61. AI Acceptance Criteria

The AI subsystem is acceptable for a production release when:

- detection model is versioned
- dataset is versioned
- inference is reproducible
- AI jobs execute asynchronously
- detection results are persisted
- confidence is recorded
- model version is recorded
- damage classes are canonical
- severity is explainable
- human review is supported
- geospatial association works
- deterioration prediction has a documented target
- leakage-resistant evaluation is completed
- repair verification is traceable
- failures are explicit
- model artifacts are controlled
- monitoring exists
- historical AI results are preserved
- no external generative AI API is required

---

# 62. Coding-Agent Rules for AI/ML

Any coding agent implementing the AI subsystem must:

1. Read all parent documents before modifying AI code.
2. Never invent a new AI architecture without documenting the change.
3. Never replace YOLO with another detector without approval.
4. Never replace XGBoost without documenting the architectural change.
5. Never introduce an external AI API.
6. Never hard-code production confidence thresholds without validation.
7. Never equate detection confidence with physical severity.
8. Never delete historical AI results.
9. Never overwrite model versions.
10. Never silently change class mappings.
11. Never create duplicate damage records during retries.
12. Never bypass human review requirements.
13. Never load arbitrary model artifacts.
14. Never place model binaries in source control.
15. Never use future information when constructing prediction features.
16. Never claim a model is accurate without evaluation evidence.
17. Never fabricate model output for production functionality.
18. Preserve model, dataset, preprocessing, and feature version metadata.
19. Update documentation when AI architecture changes.
20. Add tests for every important AI processing component.

---

# 63. AI Definition of Done

An AI feature is considered complete only when:

```text
Requirement
    ↓
Input Validation
    ↓
AI Processing
    ↓
Output Validation
    ↓
Persistence
    ↓
Model Version Tracking
    ↓
Error Handling
    ↓
Authorization
    ↓
Tests
    ↓
Monitoring
    ↓
Documentation
```

All applicable stages must be implemented.

---

# 64. Canonical AI Flow

The final canonical AI/ML flow is:

```text
MEDIA
  ↓
VALIDATION
  ↓
PREPROCESSING
  ↓
YOLO DETECTION
  ↓
POSTPROCESSING / NMS
  ↓
DAMAGE CLASSIFICATION
  ↓
SEVERITY ASSESSMENT
  ↓
GEOLOCATION
  ↓
CANONICAL DAMAGE RECORD
  ↓
ROAD HEALTH FEATURES
  ↓
XGBOOST DETERIORATION PREDICTION
  ↓
MAINTENANCE INTELLIGENCE
  ↓
REPAIR EVIDENCE
  ↓
AI REPAIR VERIFICATION
  ↓
HUMAN REVIEW WHERE REQUIRED
  ↓
RECURRENCE
  ↓
HISTORICAL LEARNING
```

---

# 65. Final AI Principle

The AI system is not simply a pothole detector.

It is an intelligence layer connecting:

```text
OBSERVATION
   ↓
DETECTION
   ↓
CLASSIFICATION
   ↓
SEVERITY
   ↓
LOCATION
   ↓
ROAD HEALTH
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
LEARNING
```

The objective is to create an auditable, measurable and continuously improving **Road Intelligence System** rather than an isolated computer-vision demo.