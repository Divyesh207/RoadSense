import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlalchemy import select

from app.models.ai import AIDetection, AIProcessingRun
from app.models.inspection import Inspection, InspectionMedia
from app.models.jobs import ProcessingJob
from app.services.spatial import point_to_wkt
from pipelines.media_pipeline import (
    _default_media_resolver,
    execute_inspection_pipeline,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _write_defect_image(path: Path) -> Path:
    img = np.full((480, 640, 3), 130, dtype=np.uint8)
    cv2.circle(img, (320, 240), 50, (20, 20, 20), -1)
    cv2.imwrite(str(path), img)
    return path


async def _seed(async_db, media_files: list[Path], job_status: str = "QUEUED", road_ids=(None, None)):
    org_id, insp_id, job_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async_db.add(
        Inspection(
            id=insp_id,
            organization_id=org_id,
            road_id=road_ids[0],
            road_segment_id=road_ids[1],
            inspector_user_id=uuid.uuid4(),
            status="PROCESSING",
            source="API",
            captured_at=_now(),
            location=point_to_wkt(18.5204, 73.8567),
            created_at=_now(),
        )
    )
    for f in media_files:
        async_db.add(
            InspectionMedia(
                id=uuid.uuid4(),
                organization_id=org_id,
                inspection_id=insp_id,
                media_type="IMAGE",
                storage_bucket="inspection-media",
                storage_path=str(f),
                original_filename=f.name,
                mime_type="image/jpeg",
                file_size_bytes=f.stat().st_size,
                upload_status="COMPLETED",
                created_at=_now(),
            )
        )
    async_db.add(
        ProcessingJob(
            id=job_id,
            organization_id=org_id,
            job_type="INSPECTION_AI_ANALYSIS",
            entity_type="inspections",
            entity_id=insp_id,
            idempotency_key=f"inspection:{insp_id}:attempt:1",
            status=job_status,
            created_at=_now(),
        )
    )
    await async_db.commit()
    return org_id, insp_id, job_id


def _local(media) -> Path:
    return Path(media.storage_path)


@pytest.mark.asyncio
async def test_inspection_pipeline_processes_all_media_and_tolerates_one_bad_item(async_db, tmp_path):
    good_a = _write_defect_image(tmp_path / "a.jpg")
    good_b = _write_defect_image(tmp_path / "b.jpg")
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not an image")
    org_id, insp_id, job_id = await _seed(async_db, [good_a, good_b, corrupt])

    result = await execute_inspection_pipeline(
        async_db, job_id, insp_id, org_id, confidence_threshold=0.2, resolve_media=_local, worker_version="test"
    )

    assert result["status"] == "COMPLETED"
    assert result["media_total"] == 3
    assert result["media_processed"] == 2
    assert [f["error_code"] for f in result["media_failed"]] == ["CORRUPT_IMAGE"]

    job = (await async_db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job.status == "COMPLETED"
    assert job.attempts == 1
    assert job.worker_version == "test"
    assert job.result_metadata["media_processed"] == 2

    insp = (await async_db.execute(select(Inspection).where(Inspection.id == insp_id))).scalar_one()
    assert insp.status == "ANALYZED"

    runs = (await async_db.execute(select(AIProcessingRun).where(AIProcessingRun.processing_job_id == job_id))).scalars().all()
    assert len(runs) == 2
    assert all(r.output_metadata["inference_backend"] for r in runs)
    dets = (await async_db.execute(select(AIDetection).where(AIDetection.inspection_id == insp_id))).scalars().all()
    assert len(dets) == result["detection_count"] >= 2


@pytest.mark.asyncio
async def test_inspection_pipeline_fails_when_every_item_fails(async_db, tmp_path):
    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"garbage")
    org_id, insp_id, job_id = await _seed(async_db, [corrupt])

    result = await execute_inspection_pipeline(async_db, job_id, insp_id, org_id, resolve_media=_local)

    assert result["status"] == "FAILED"
    assert result["error_code"] == "CORRUPT_IMAGE"
    job = (await async_db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job.status == "FAILED"
    assert job.failed_at is not None
    insp = (await async_db.execute(select(Inspection).where(Inspection.id == insp_id))).scalar_one()
    assert insp.status == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_inspection_pipeline_without_media_fails_cleanly(async_db):
    org_id, insp_id, job_id = await _seed(async_db, [])

    result = await execute_inspection_pipeline(async_db, job_id, insp_id, org_id, resolve_media=_local)

    assert result["error_code"] == "NO_MEDIA"
    insp = (await async_db.execute(select(Inspection).where(Inspection.id == insp_id))).scalar_one()
    assert insp.status == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_inspection_pipeline_skips_redelivered_job(async_db, tmp_path):
    good = _write_defect_image(tmp_path / "a.jpg")
    org_id, insp_id, job_id = await _seed(async_db, [good], job_status="COMPLETED")

    result = await execute_inspection_pipeline(async_db, job_id, insp_id, org_id, resolve_media=_local)

    assert result["status"] == "SKIPPED"
    runs = (await async_db.execute(select(AIProcessingRun).where(AIProcessingRun.processing_job_id == job_id))).scalars().all()
    assert runs == []


def test_default_resolver_reads_shared_local_storage(tmp_path, monkeypatch):
    from app.core.config import settings
    from preprocessing.validator import MediaValidationError

    target = tmp_path / "inspection-media" / "inspections" / "x" / "photo.jpg"
    target.parent.mkdir(parents=True)
    _write_defect_image(target)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ROOT", str(tmp_path))

    class _Media:
        storage_bucket = "inspection-media"
        storage_path = "inspections/x/photo.jpg"

    assert _default_media_resolver(_Media()) == target.resolve()

    _Media.storage_path = "inspections/x/missing.jpg"
    with pytest.raises(MediaValidationError) as exc:
        _default_media_resolver(_Media())
    assert exc.value.code == "MEDIA_UNAVAILABLE"

    _Media.storage_path = "../../outside.jpg"
    with pytest.raises(MediaValidationError):
        _default_media_resolver(_Media())


@pytest.mark.asyncio
async def test_fallback_runs_record_heuristic_provenance(async_db, tmp_path):
    from app.models.ai import AIModel

    good = _write_defect_image(tmp_path / "a.jpg")
    org_id, insp_id, job_id = await _seed(async_db, [good])

    await execute_inspection_pipeline(async_db, job_id, insp_id, org_id, confidence_threshold=0.2, resolve_media=_local)

    run = (await async_db.execute(select(AIProcessingRun).where(AIProcessingRun.processing_job_id == job_id))).scalar_one()
    assert run.output_metadata["inference_backend"] == "opencv-heuristic"
    assert "not found" in run.output_metadata["backend_metadata"]["fallback_reason"]
    model = (await async_db.execute(select(AIModel).where(AIModel.id == run.model_id))).scalar_one()
    assert model.name == "opencv-heuristic-road-damage"
    assert model.model_family == "OPENCV_HEURISTIC"
    assert not model.metrics


@pytest.mark.asyncio
async def test_strict_mode_fails_job_when_trained_model_missing(async_db, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_REQUIRE_TRAINED_MODEL", "true")
    good = _write_defect_image(tmp_path / "a.jpg")
    org_id, insp_id, job_id = await _seed(async_db, [good])

    result = await execute_inspection_pipeline(async_db, job_id, insp_id, org_id, resolve_media=_local)

    assert result["error_code"] == "MODEL_UNAVAILABLE"
    job = (await async_db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job.status == "FAILED"
    insp = (await async_db.execute(select(Inspection).where(Inspection.id == insp_id))).scalar_one()
    assert insp.status == "PROCESSING_FAILED"


@pytest.mark.asyncio
async def test_road_linked_inspection_stores_json_safe_association(async_db, tmp_path):
    """raw_output is JSONB: the road/segment UUIDs must be serialized as strings."""
    road_id, segment_id = uuid.uuid4(), uuid.uuid4()
    good = _write_defect_image(tmp_path / "a.jpg")
    org_id, insp_id, job_id = await _seed(async_db, [good], road_ids=(road_id, segment_id))

    result = await execute_inspection_pipeline(
        async_db, job_id, insp_id, org_id, confidence_threshold=0.2, resolve_media=_local
    )

    assert result["status"] == "COMPLETED", result
    det = (await async_db.execute(select(AIDetection).where(AIDetection.inspection_id == insp_id))).scalars().first()
    assoc = det.raw_output["geospatial_association"]
    assert assoc["road_id"] == str(road_id)
    assert assoc["road_segment_id"] == str(segment_id)
