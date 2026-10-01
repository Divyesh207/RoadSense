import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest
from app.models.ai import AIDetection, AIProcessingRun
from app.models.inspection import Inspection, InspectionMedia
from app.models.jobs import ProcessingJob
from app.services.spatial import point_to_wkt
from pipelines.media_pipeline import execute_media_pipeline
from sqlalchemy import select


@pytest.fixture
def test_defect_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "defect_road.jpg"
    img = np.full((480, 640, 3), 130, dtype=np.uint8)
    # Draw dark pothole defect
    cv2.circle(img, (320, 240), 50, (20, 20, 20), -1)
    cv2.imwrite(str(img_path), img)
    return img_path


@pytest.fixture
def test_corrupt_file(tmp_path: Path) -> Path:
    p = tmp_path / "corrupt.jpg"
    p.write_bytes(b"corrupted garbage")
    return p


@pytest.mark.asyncio
async def test_execute_media_pipeline_success(async_db, test_defect_image: Path):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    insp_id = uuid.uuid4()
    media_id = uuid.uuid4()
    job_id = uuid.uuid4()

    # 1. Create parent Inspection
    insp = Inspection(
        id=insp_id,
        organization_id=org_id,
        inspector_user_id=user_id,
        status="SUBMITTED",
        source="API",
        captured_at=datetime.now(timezone.utc),
        location=point_to_wkt(18.5204, 73.8567),
        gps_accuracy_meters=3.5,
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(insp)

    # 2. Create InspectionMedia
    media = InspectionMedia(
        id=media_id,
        organization_id=org_id,
        inspection_id=insp_id,
        media_type="IMAGE",
        storage_bucket="inspection-media",
        storage_path=str(test_defect_image),
        original_filename="defect_road.jpg",
        mime_type="image/jpeg",
        file_size_bytes=test_defect_image.stat().st_size,
        upload_status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(media)

    # 3. Create ProcessingJob in QUEUED status
    job = ProcessingJob(
        id=job_id,
        organization_id=org_id,
        job_type="AI_DETECTION",
        entity_type="INSPECTION_MEDIA",
        entity_id=media_id,
        idempotency_key=f"ai_detect_{job_id}",
        status="QUEUED",
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(job)
    await async_db.commit()

    # 4. Execute AI pipeline
    result = await execute_media_pipeline(
        db=async_db,
        job_id=job_id,
        media_id=media_id,
        organization_id=org_id,
        file_path=test_defect_image,
        confidence_threshold=0.20,
    )

    assert result["status"] == "COMPLETED"
    assert result["detection_count"] >= 1

    # 5. Verify ProcessingJob state transition to COMPLETED
    job_refreshed = (await async_db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job_refreshed.status == "COMPLETED"
    assert job_refreshed.started_at is not None
    assert job_refreshed.completed_at is not None
    assert job_refreshed.result_metadata["detection_count"] == result["detection_count"]

    # 6. Verify AIProcessingRun provenance
    run_refreshed = (await async_db.execute(select(AIProcessingRun).where(AIProcessingRun.id == result["run_id"]))).scalar_one()
    assert run_refreshed.status == "COMPLETED"
    assert run_refreshed.model_id is not None
    assert run_refreshed.configuration_version == "1.0.0"
    assert run_refreshed.input_metadata["media_type"] == "IMAGE"

    # 7. Verify AIDetection records
    dets = (await async_db.execute(select(AIDetection).where(AIDetection.ai_processing_run_id == run_refreshed.id))).scalars().all()
    assert len(dets) == result["detection_count"]
    first_det = dets[0]
    assert 0.0 <= first_det.confidence <= 1.0
    assert 0.0 <= first_det.bbox_x_min < first_det.bbox_x_max <= 1.0
    assert 0.0 <= first_det.bbox_y_min < first_det.bbox_y_max <= 1.0
    assert "severity_assessment" in first_det.raw_output
    assert first_det.raw_output["severity_assessment"]["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


@pytest.mark.asyncio
async def test_execute_media_pipeline_corrupt_media_fails_gracefully(async_db, test_corrupt_file: Path):
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    insp_id = uuid.uuid4()
    media_id = uuid.uuid4()
    job_id = uuid.uuid4()

    insp = Inspection(
        id=insp_id,
        organization_id=org_id,
        inspector_user_id=user_id,
        status="SUBMITTED",
        source="API",
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(insp)

    media = InspectionMedia(
        id=media_id,
        organization_id=org_id,
        inspection_id=insp_id,
        media_type="IMAGE",
        storage_bucket="inspection-media",
        storage_path=str(test_corrupt_file),
        original_filename="corrupt.jpg",
        mime_type="image/jpeg",
        file_size_bytes=test_corrupt_file.stat().st_size,
        upload_status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(media)

    job = ProcessingJob(
        id=job_id,
        organization_id=org_id,
        job_type="AI_DETECTION",
        entity_type="INSPECTION_MEDIA",
        entity_id=media_id,
        idempotency_key=f"ai_detect_{job_id}",
        status="QUEUED",
        created_at=datetime.now(timezone.utc),
    )
    async_db.add(job)
    await async_db.commit()

    # Pipeline should gracefully catch validation error and mark job FAILED
    result = await execute_media_pipeline(
        db=async_db,
        job_id=job_id,
        media_id=media_id,
        organization_id=org_id,
        file_path=test_corrupt_file,
    )

    assert result["status"] == "FAILED"
    assert result["error_code"] == "CORRUPT_IMAGE"

    job_refreshed = (await async_db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job_refreshed.status == "FAILED"
    assert "CORRUPT_IMAGE" in job_refreshed.error_message
