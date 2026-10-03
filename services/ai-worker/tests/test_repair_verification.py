"""Repair verification: image analysis rules and the worker job, on SYNTHETIC image pairs.

All images here are constructed (see tests/synthetic_repair.py) and the detector is a
deterministic stand-in; these tests validate software behaviour, not real-world accuracy.
"""

import uuid
from datetime import datetime, timezone

import numpy as np
import pytest
from sqlalchemy import select
from verification.repair_analysis import ALGORITHM_VERSION, Box, analyze_repair_pair

from app.models.ai import AIProcessingRun
from app.models.jobs import ProcessingJob
from app.models.maintenance import MaintenanceJob
from app.models.repair import RepairEvidence, RepairVerification
from inference.detector import BaseDetector, DetectionResult
from pipelines.repair_pipeline import TransientStorageError, execute_repair_verification
from postprocessing.nms import RawDetection
from tests.synthetic_repair import (
    SequenceDetector,
    asphalt,
    dark_blob_detector,
    encode,
    reshoot,
    with_patch,
    with_pothole,
)

ORG = uuid.UUID("11111111-1111-1111-1111-111111111111")
POTHOLE_BOX = Box("POTHOLE", 0.8, 0.36, 0.40, 0.64, 0.66)


@pytest.fixture(scope="module")
def pair():
    before = with_pothole(asphalt())
    return {
        "before": encode(before),
        "repaired": encode(reshoot(with_patch(before))),
        "residual": encode(reshoot(before)),
        "unchanged": encode(reshoot(before, shift=10, brightness=4)),
        "elsewhere": encode(reshoot(with_pothole(asphalt(seed=99)))),
    }


# --- analysis rules -------------------------------------------------------------------------


def test_successful_repair_when_region_changed_and_no_residual_damage(pair):
    r = analyze_repair_pair(pair["before"], pair["repaired"], dark_blob_detector)
    assert r.result == "SUCCESSFUL", r.reasons
    assert r.reason_code == "DAMAGE_REGION_REPAIRED"
    assert r.checks["alignment"]["aligned"] is True
    assert len(r.before_detections) == 1 and r.after_detections == [] and r.residual_detections == []
    region = r.metrics["region"]
    assert region["change_contrast"] >= 1.5
    assert region["region_ssim"] < region["background_ssim"] - 0.10
    findings = r.findings()
    assert findings["image_comparison_performed"] is True
    assert findings["before_detection_count"] == 1 and findings["after_detection_count"] == 0


def test_residual_damage_in_after_image_is_substandard(pair):
    r = analyze_repair_pair(pair["before"], pair["residual"], dark_blob_detector)
    assert r.result == "SUBSTANDARD"
    assert r.reason_code == "RESIDUAL_DAMAGE_DETECTED"
    assert len(r.residual_detections) == 1
    assert r.residual_detections[0]["damage_type"] == "POTHOLE"


def test_no_detection_but_unchanged_region_is_unresolved(pair):
    # The detector misses the pothole in the AFTER image although nothing was repaired.
    r = analyze_repair_pair(pair["before"], pair["unchanged"], SequenceDetector([POTHOLE_BOX], []))
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "REGION_UNCHANGED"


def test_no_documented_damage_in_before_image_is_unresolved(pair):
    r = analyze_repair_pair(pair["before"], pair["repaired"], SequenceDetector([], []))
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "BEFORE_DAMAGE_NOT_DETECTED"


def test_different_location_fails_alignment(pair):
    r = analyze_repair_pair(pair["before"], pair["elsewhere"], dark_blob_detector)
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "ALIGNMENT_FAILED"
    assert r.checks["alignment"]["aligned"] is False
    # Detection still ran on both images so counts are reported.
    assert len(r.before_detections) == 1 and len(r.after_detections) == 1


def test_featureless_images_are_unresolved():
    flat = np.full((720, 960, 3), 120, np.uint8)
    flat[100:400, 100:400] = 30
    flat[200:600, 500:800] = 220
    r = analyze_repair_pair(encode(flat), encode(flat), dark_blob_detector)
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "INSUFFICIENT_FEATURES"


def test_corrupted_image_is_unresolved(pair):
    r = analyze_repair_pair(pair["before"], b"\xff\xd8\xff not really a jpeg", dark_blob_detector)
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "IMAGE_DECODE_FAILED"


def test_poor_quality_images_are_unresolved(pair):
    dark = np.full((720, 960, 3), 5, np.uint8)
    r = analyze_repair_pair(pair["before"], encode(dark), dark_blob_detector)
    assert r.result == "UNRESOLVED"
    assert r.reason_code == "POOR_IMAGE_QUALITY"
    tiny = encode(asphalt()[:100, :100])
    assert analyze_repair_pair(tiny, tiny, dark_blob_detector).reason_code == "POOR_IMAGE_QUALITY"


def test_analysis_is_deterministic(pair):
    a = analyze_repair_pair(pair["before"], pair["repaired"], dark_blob_detector)
    b = analyze_repair_pair(pair["before"], pair["repaired"], dark_blob_detector)
    assert (a.result, a.metrics, a.before_detections) == (b.result, b.metrics, b.before_detections)


# --- worker job -----------------------------------------------------------------------------


class BlobDetector(BaseDetector):
    """BaseDetector wrapper around the synthetic dark-blob stand-in (tests only)."""

    model_id = "test-blob-detector"
    model_version = "test"
    backend = "test-stand-in"
    recommended_confidence_threshold = 0.5

    def __init__(self):
        self.thresholds = []

    def detect(self, image, confidence_threshold=0.25, iou_threshold=0.45, frame_number=None, frame_timestamp_ms=None):
        self.thresholds.append(confidence_threshold)
        boxes = dark_blob_detector(image)
        return DetectionResult(
            detections=[RawDetection(b.damage_type_code, b.confidence, b.x_min, b.y_min, b.x_max, b.y_max) for b in boxes],
            model_id=self.model_id, model_version=self.model_version, inference_time_ms=1.0,
            image_width=image.shape[1], image_height=image.shape[0], confidence_threshold=confidence_threshold,
            raw_detections_count=len(boxes), backend=self.backend,
        )


async def seed(db, before_bytes, after_bytes, job_status="QUEUED"):
    now = datetime.now(timezone.utc)
    job = MaintenanceJob(id=uuid.uuid4(), organization_id=ORG, created_by_user_id=uuid.uuid4(), title="Repair",
                         priority_level="HIGH", status="VERIFICATION_PENDING", created_at=now, updated_at=now)
    store = {}
    evidence = []
    for kind, data in (("BEFORE_REPAIR", before_bytes), ("AFTER_REPAIR", after_bytes)):
        ev = RepairEvidence(id=uuid.uuid4(), organization_id=ORG, maintenance_job_id=job.id,
                            uploaded_by_user_id=uuid.uuid4(), evidence_type=kind, storage_bucket="repair-evidence",
                            storage_path=f"{job.id}/{kind}.jpg", media_type="IMAGE", mime_type="image/jpeg",
                            created_at=now, updated_at=now)
        store[(ev.storage_bucket, ev.storage_path)] = data
        evidence.append(ev)
    pjob = ProcessingJob(id=uuid.uuid4(), organization_id=ORG, job_type="REPAIR_VERIFICATION",
                         entity_type="maintenance_job", entity_id=job.id, idempotency_key=f"k-{uuid.uuid4()}",
                         status=job_status, max_attempts=3, queued_at=now, created_at=now, updated_at=now)
    ver = RepairVerification(id=uuid.uuid4(), organization_id=ORG, maintenance_job_id=job.id,
                             verification_status="QUEUED", verification_type="AUTOMATED_IMAGE_ANALYSIS",
                             before_evidence_id=evidence[0].id, after_evidence_id=evidence[1].id,
                             processing_job_id=pjob.id, findings={}, created_at=now, updated_at=now)
    db.add_all([job, *evidence, pjob, ver])
    await db.commit()
    return pjob, ver, store


@pytest.mark.asyncio
async def test_worker_job_persists_result_with_model_provenance(async_db, pair):
    pjob, ver, store = await seed(async_db, pair["before"], pair["repaired"])
    detector = BlobDetector()
    out = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=lambda b, p: store[(b, p)],
                                            detector=detector)
    assert out["status"] == "COMPLETED" and out["result"] == "SUCCESSFUL"
    await async_db.refresh(ver)
    await async_db.refresh(pjob)
    assert (ver.verification_status, ver.result) == ("COMPLETED", "SUCCESSFUL")
    assert (ver.model_name, ver.model_version) == ("test-blob-detector", "test")
    assert ver.algorithm_version == ALGORITHM_VERSION
    assert ver.ai_confidence is None
    assert ver.findings["model"]["confidence_threshold"] == 0.5
    assert detector.thresholds == [0.5, 0.5]  # configured threshold used for both images
    assert pjob.status == "COMPLETED" and pjob.attempts == 1
    run = await async_db.get(AIProcessingRun, ver.ai_processing_run_id)
    assert run.run_type == "REPAIR_VERIFICATION" and run.output_metadata["result"] == "SUCCESSFUL"


@pytest.mark.asyncio
async def test_worker_job_is_idempotent_for_redelivered_messages(async_db, pair):
    pjob, ver, store = await seed(async_db, pair["before"], pair["residual"])
    reader = lambda b, p: store[(b, p)]
    first = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=reader, detector=BlobDetector())
    again = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=reader, detector=BlobDetector())
    assert first["result"] == "SUBSTANDARD"
    assert again["status"] == "SKIPPED"
    runs = (await async_db.execute(select(AIProcessingRun))).scalars().all()
    assert len(runs) == 1


@pytest.mark.asyncio
async def test_transient_storage_failure_requeues_then_fails_after_max_attempts(async_db, pair):
    pjob, ver, _ = await seed(async_db, pair["before"], pair["repaired"])

    def broken(bucket, path):
        raise TransientStorageError("storage timeout")

    for attempt in (1, 2):
        out = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=broken, detector=BlobDetector())
        assert out["status"] == "RETRY" and out["attempts"] == attempt
        await async_db.refresh(pjob)
        assert pjob.status == "QUEUED"
    out = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=broken, detector=BlobDetector())
    assert out["status"] == "FAILED" and out["error_code"] == "STORAGE_UNAVAILABLE"
    await async_db.refresh(ver)
    assert ver.verification_status == "FAILED" and ver.result is None


@pytest.mark.asyncio
async def test_missing_trained_model_fails_instead_of_guessing(async_db, pair, monkeypatch):
    monkeypatch.setenv("AI_REQUIRE_TRAINED_MODEL", "true")
    pjob, ver, store = await seed(async_db, pair["before"], pair["repaired"])
    out = await execute_repair_verification(async_db, pjob.id, ver.id, ORG, read_object=lambda b, p: store[(b, p)])
    assert out["status"] == "FAILED" and out["error_code"] == "MODEL_UNAVAILABLE"
    await async_db.refresh(ver)
    assert ver.result is None
