import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inference.detector import BaseDetector, DetectionResult
from inference.model_registry import (
    FALLBACK_MODEL_ID,
    FALLBACK_MODEL_VERSION,
    ModelRegistry,
    TrainedModelRequiredError,
)
from postprocessing.nms import RawDetection, suppress_temporal_duplicates
from postprocessing.severity import assess_damage_severity
from postprocessing.spatial import associate_detection_location
from preprocessing.image import preprocess_image
from preprocessing.validator import (
    MediaValidationError,
    ValidationResult,
    validate_media_file,
)
from preprocessing.video import sample_video_frames
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

PIPELINE_CONFIGURATION_VERSION = "1.0.0"

# Resolves an InspectionMedia row to a readable local file (downloading it from
# object storage when necessary). Injected so tests and callers can override it.
MediaResolver = Callable[[Any], Path]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    """JSONB columns are serialized with json.dumps; UUIDs (road/segment ids) are not JSON."""
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


@dataclass
class MediaAnalysis:
    """Output of the compute-only stage for one media item (no DB writes)."""

    validation: ValidationResult
    detections: list[tuple[RawDetection, dict[str, Any]]]
    inference_time_ms: float
    model_id: str
    model_version: str
    backend: str
    backend_metadata: dict[str, Any] = field(default_factory=dict)


async def ensure_damage_types(db: AsyncSession) -> dict[str, uuid.UUID]:
    """Ensures base damage types exist and returns mapping of code -> ID."""
    from app.models.ai import DamageType

    base_types = [
        ("POTHOLE", "Pothole", "A hole or structural cavity in a road surface caused by wear or weather."),
        ("CRACK", "Surface Crack", "Linear fractures or fissures in the road pavement."),
        ("DEPRESSION", "Depression / Rutting", "Sunken road surface area causing surface deformation."),
        ("WATERLOGGING", "Waterlogging", "Accumulation of standing water on the road indicating drainage failure."),
        ("SURFACE_DAMAGE", "Surface Damage / Ravelling", "Loss of aggregate, peeling, or general surface deterioration."),
        ("OTHER", "Other Unclassified Damage", "Road surface defect not fitting primary standard classes."),
    ]

    mapping: dict[str, uuid.UUID] = {}
    for code, name, desc in base_types:
        stmt = select(DamageType).where(DamageType.code == code)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if not existing:
            dt = DamageType(
                id=uuid.uuid4(),
                code=code,
                name=name,
                description=desc,
                is_active=True,
                created_at=utc_now(),
            )
            db.add(dt)
            await db.flush()
            mapping[code] = dt.id
        else:
            mapping[code] = existing.id

    return mapping


async def ensure_ai_model(
    db: AsyncSession, model_id_name: str = FALLBACK_MODEL_ID, version: str = FALLBACK_MODEL_VERSION
) -> uuid.UUID:
    """Ensures AI model record exists in ai_models table and returns its UUID."""
    from app.models.ai import AIModel

    stmt = select(AIModel).where(AIModel.name == model_id_name, AIModel.version == version)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing.id

    registry = ModelRegistry()
    info = registry.get_model_info(model_id_name, version)
    ai_m = AIModel(
        id=uuid.uuid4(),
        name=model_id_name,
        model_family=info.model_family if info else "YOLO",
        model_type=info.model_type if info else "OBJECT_DETECTION",
        version=version,
        artifact_uri=info.artifact_uri if info else f"local://models/{model_id_name}.pt",
        artifact_checksum=(info.metadata.get("weights_sha256") if info else None),
        framework=info.framework if info else "PyTorch",
        status="ACTIVE",
        metrics=info.metrics if info else None,
        metadata_=info.metadata if info else None,
        deployed_at=utc_now(),
        created_at=utc_now(),
    )
    db.add(ai_m)
    await db.flush()
    return ai_m.id


def analyze_media_file(
    target_file: Path,
    expected_media_type: str | None,
    detector: BaseDetector,
    confidence_threshold: float,
    iou_threshold: float,
) -> MediaAnalysis:
    """Validation, preprocessing, detection, NMS and severity for one file.
    Raises MediaValidationError for unusable media."""
    validation = validate_media_file(target_file, expected_type=expected_media_type)

    detections: list[tuple[RawDetection, dict[str, Any]]] = []
    total_inference_time_ms = 0.0
    last_result: DetectionResult | None = None

    if validation.media_type == "IMAGE":
        prep = preprocess_image(str(target_file))
        last_result = detector.detect(
            prep.original_image,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
        )
        total_inference_time_ms += last_result.inference_time_ms
        for det in last_result.detections:
            severity_eval = assess_damage_severity(
                damage_type_code=det.damage_type_code,
                bbox_x_min=det.bbox_x_min,
                bbox_y_min=det.bbox_y_min,
                bbox_x_max=det.bbox_x_max,
                bbox_y_max=det.bbox_y_max,
                pixel_width=prep.orig_width,
                pixel_height=prep.orig_height,
            )
            detections.append((det, severity_eval.__dict__))

    elif validation.media_type == "VIDEO":
        all_frame_detections: list[RawDetection] = []
        for frame_obj in sample_video_frames(target_file, sample_fps=1.0, max_frames=60):
            last_result = detector.detect(
                frame_obj.image,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
                frame_number=frame_obj.frame_number,
                frame_timestamp_ms=frame_obj.timestamp_ms,
            )
            total_inference_time_ms += last_result.inference_time_ms
            all_frame_detections.extend(last_result.detections)

        # Suppress temporal duplicates across video frames
        for det in suppress_temporal_duplicates(all_frame_detections):
            severity_eval = assess_damage_severity(
                damage_type_code=det.damage_type_code,
                bbox_x_min=det.bbox_x_min,
                bbox_y_min=det.bbox_y_min,
                bbox_x_max=det.bbox_x_max,
                bbox_y_max=det.bbox_y_max,
                pixel_width=validation.width_px,
                pixel_height=validation.height_px,
            )
            detections.append((det, severity_eval.__dict__))

    return MediaAnalysis(
        validation=validation,
        detections=detections,
        inference_time_ms=total_inference_time_ms,
        model_id=last_result.model_id if last_result else detector.model_id,
        model_version=last_result.model_version if last_result else detector.model_version,
        backend=last_result.backend if last_result else detector.backend,
        backend_metadata=last_result.backend_metadata if last_result else {},
    )


async def persist_media_analysis(
    db: AsyncSession,
    job: Any,
    media: Any,
    inspection: Any,
    analysis: MediaAnalysis,
    confidence_threshold: float,
    started_at: datetime,
    damage_type_map: dict[str, uuid.UUID],
) -> tuple[Any, list[uuid.UUID]]:
    """Creates the AIProcessingRun and AIDetection rows for one analyzed media item."""
    from app.models.ai import AIDetection, AIProcessingRun
    from app.services.spatial import point_to_wkt, wkt_or_geom_to_point

    model_uuid = await ensure_ai_model(db, analysis.model_id, analysis.model_version)
    validation = analysis.validation

    t_comp = utc_now()
    run = AIProcessingRun(
        id=uuid.uuid4(),
        organization_id=media.organization_id,
        processing_job_id=job.id,
        model_id=model_uuid,
        inspection_id=media.inspection_id,
        media_id=media.id,
        run_type="INSPECTION_DETECTION",
        configuration_version=PIPELINE_CONFIGURATION_VERSION,
        confidence_threshold=confidence_threshold,
        input_metadata={
            "media_type": validation.media_type,
            "mime_type": validation.mime_type,
            "dimensions": [validation.width_px, validation.height_px],
            "file_size": validation.file_size_bytes,
        },
        output_metadata={
            "detection_count": len(analysis.detections),
            "inference_time_ms": analysis.inference_time_ms,
            "model_name": analysis.model_id,
            "model_version": analysis.model_version,
            "inference_backend": analysis.backend,
            **({"backend_metadata": analysis.backend_metadata} if analysis.backend_metadata else {}),
        },
        status="COMPLETED",
        started_at=started_at,
        completed_at=t_comp,
        created_at=started_at,
    )
    db.add(run)
    await db.flush()

    # Extract GPS from parent inspection
    insp_coords = wkt_or_geom_to_point(inspection.location) if inspection else None
    insp_lat = insp_coords[0] if insp_coords else None
    insp_lon = insp_coords[1] if insp_coords else None

    geo_assoc = associate_detection_location(
        detection_lat=insp_lat,
        detection_lon=insp_lon,
        fallback_road_id=inspection.road_id if inspection else None,
        fallback_segment_id=inspection.road_segment_id if inspection else None,
    )

    pt_geom = point_to_wkt(insp_lat, insp_lon) if (insp_lat is not None and insp_lon is not None) else None

    detection_ids: list[uuid.UUID] = []
    for det, sev_data in analysis.detections:
        dt_id = damage_type_map.get(det.damage_type_code) or damage_type_map.get("OTHER")
        ai_det = AIDetection(
            id=uuid.uuid4(),
            organization_id=media.organization_id,
            ai_processing_run_id=run.id,
            inspection_id=media.inspection_id,
            media_id=media.id,
            damage_type_id=dt_id,
            frame_number=det.frame_number,
            frame_timestamp_ms=det.frame_timestamp_ms,
            confidence=det.confidence,
            bbox_x_min=det.bbox_x_min,
            bbox_y_min=det.bbox_y_min,
            bbox_x_max=det.bbox_x_max,
            bbox_y_max=det.bbox_y_max,
            pixel_width=validation.width_px,
            pixel_height=validation.height_px,
            location=pt_geom,
            raw_output={
                "severity_assessment": sev_data,
                "geospatial_association": _json_safe(geo_assoc.__dict__),
                "metadata": det.metadata,
            },
            created_at=t_comp,
        )
        db.add(ai_det)
        detection_ids.append(ai_det.id)

    return run, detection_ids


async def _mark_job_failed(
    db: AsyncSession,
    job: Any,
    error_code: str,
    error_message: str,
    result_metadata: dict[str, Any] | None = None,
    inspection: Any = None,
) -> None:
    job.status = "FAILED"
    job.completed_at = utc_now()
    job.failed_at = job.completed_at
    job.error_code = error_code
    job.error_message = error_message
    if result_metadata is not None:
        job.result_metadata = result_metadata
    if inspection is not None:
        inspection.status = "PROCESSING_FAILED"
        inspection.updated_at = utc_now()
    await db.commit()


async def execute_media_pipeline(
    db: AsyncSession,
    job_id: uuid.UUID,
    media_id: uuid.UUID,
    organization_id: uuid.UUID,
    file_path: str | Path | None = None,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
) -> dict[str, Any]:
    """
    Executes the full AI pipeline on a single inspection media item:
    1. Updates ProcessingJob to RUNNING
    2. Validates media
    3. Runs OpenCV preprocessing and detection
    4. Applies NMS and severity assessment
    5. Creates AIProcessingRun and AIDetection records
    6. Updates ProcessingJob to COMPLETED (or FAILED on error)
    """
    from app.models.inspection import Inspection, InspectionMedia
    from app.models.jobs import ProcessingJob

    t_start = utc_now()

    job_stmt = select(ProcessingJob).where(
        ProcessingJob.id == job_id,
        ProcessingJob.organization_id == organization_id,
    )
    job = (await db.execute(job_stmt)).scalar_one_or_none()
    if not job:
        raise ValueError(f"ProcessingJob {job_id} not found for org {organization_id}")

    job.status = "RUNNING"
    job.started_at = t_start
    await db.commit()

    media_stmt = select(InspectionMedia).where(
        InspectionMedia.id == media_id,
        InspectionMedia.organization_id == organization_id,
    )
    media = (await db.execute(media_stmt)).scalar_one_or_none()
    if not media:
        await _mark_job_failed(db, job, "MEDIA_NOT_FOUND", f"InspectionMedia {media_id} not found")
        raise ValueError(job.error_message)

    insp_stmt = select(Inspection).where(Inspection.id == media.inspection_id)
    inspection = (await db.execute(insp_stmt)).scalar_one_or_none()

    target_file = Path(file_path) if file_path else Path(media.storage_path)

    try:
        detector = ModelRegistry().get_detector()
        analysis = analyze_media_file(target_file, media.media_type, detector, confidence_threshold, iou_threshold)
        damage_type_map = await ensure_damage_types(db)
        run, detection_ids = await persist_media_analysis(
            db, job, media, inspection, analysis, confidence_threshold, t_start, damage_type_map
        )

        job.status = "COMPLETED"
        job.completed_at = utc_now()
        job.result_metadata = {
            "processing_run_id": str(run.id),
            "detection_count": len(detection_ids),
            "inference_duration_ms": analysis.inference_time_ms,
            "inference_backend": analysis.backend,
            "status": "COMPLETED",
        }
        await db.commit()

        logger.info(
            "AI pipeline completed for job %s, run %s: %d detections persisted (backend=%s).",
            job_id, run.id, len(detection_ids), analysis.backend,
        )

        return {
            "status": "COMPLETED",
            "job_id": job.id,
            "run_id": run.id,
            "detection_count": len(detection_ids),
            "detection_ids": detection_ids,
        }

    except MediaValidationError as mve:
        await db.rollback()
        await _mark_job_failed(
            db, job, mve.code, f"Validation failed ({mve.code}): {mve!s}",
            {"error_code": mve.code, "error_details": mve.details},
        )
        logger.error("Job %s failed media validation: %s", job_id, mve)
        return {"status": "FAILED", "job_id": job_id, "error_code": mve.code, "error_message": str(mve)}

    except Exception as e:
        await db.rollback()
        await _mark_job_failed(db, job, "INFERENCE_ERROR", f"Inference pipeline error: {e!s}")
        logger.exception("Job %s failed with unexpected error", job_id)
        return {"status": "FAILED", "job_id": job_id, "error_message": str(e)}


def _default_media_resolver(media: Any) -> Path:
    """Materializes the media object as a local file via the configured storage
    backend (Supabase download, or the shared LOCAL_STORAGE_ROOT). Absolute paths
    already on disk are used as-is."""
    from app.services.storage import StorageError, get_storage_backend

    stored = Path(media.storage_path)
    if stored.is_absolute() and stored.is_file():
        return stored
    try:
        return get_storage_backend().fetch_to_local_path(media.storage_bucket, media.storage_path)
    except StorageError as exc:
        raise MediaValidationError(
            f"Media object {media.storage_bucket}/{media.storage_path} is not available to the worker: {exc}",
            code="MEDIA_UNAVAILABLE",
            details={"storage_bucket": media.storage_bucket, "storage_path": media.storage_path},
        ) from exc


async def execute_inspection_pipeline(
    db: AsyncSession,
    job_id: uuid.UUID,
    inspection_id: uuid.UUID,
    organization_id: uuid.UUID,
    confidence_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    resolve_media: MediaResolver | None = None,
    worker_version: str | None = None,
) -> dict[str, Any]:
    """
    Processes every completed media item of an inspection under one ProcessingJob
    (the unit the API enqueues via POST /inspections/{id}/process).

    - Redelivered tasks for a job that is no longer QUEUED are skipped (idempotent).
    - Each media item gets its own AIProcessingRun; per-item media failures are
      recorded without discarding the other items' results.
    - Job COMPLETED + inspection ANALYZED when at least one item succeeded;
      otherwise job FAILED + inspection PROCESSING_FAILED.
    """
    from app.models.inspection import Inspection, InspectionMedia
    from app.models.jobs import ProcessingJob

    resolve_media = resolve_media or _default_media_resolver

    job = (
        await db.execute(
            select(ProcessingJob).where(
                ProcessingJob.id == job_id,
                ProcessingJob.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if job is None:
        raise ValueError(f"ProcessingJob {job_id} not found for org {organization_id}")

    if job.status != "QUEUED":
        logger.warning("Job %s is %s, not QUEUED; skipping duplicate delivery.", job_id, job.status)
        return {"status": "SKIPPED", "job_id": job_id, "job_status": job.status}

    inspection = (
        await db.execute(
            select(Inspection).where(
                Inspection.id == inspection_id,
                Inspection.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()

    t_start = utc_now()
    job.status = "RUNNING"
    job.started_at = t_start
    job.attempts = (job.attempts or 0) + 1
    if worker_version:
        job.worker_version = worker_version
    await db.commit()

    if inspection is None:
        await _mark_job_failed(db, job, "INSPECTION_NOT_FOUND", f"Inspection {inspection_id} not found")
        return {"status": "FAILED", "job_id": job_id, "error_code": "INSPECTION_NOT_FOUND"}

    media_items = (
        await db.execute(
            select(InspectionMedia)
            .where(
                InspectionMedia.inspection_id == inspection_id,
                InspectionMedia.organization_id == organization_id,
                InspectionMedia.upload_status == "COMPLETED",
            )
            .order_by(InspectionMedia.created_at.asc())
        )
    ).scalars().all()

    if not media_items:
        await _mark_job_failed(
            db, job, "NO_MEDIA", "Inspection has no completed media to analyze.", inspection=inspection
        )
        return {"status": "FAILED", "job_id": job_id, "error_code": "NO_MEDIA"}

    try:
        detector = ModelRegistry().get_detector()
    except TrainedModelRequiredError as exc:
        await _mark_job_failed(db, job, "MODEL_UNAVAILABLE", str(exc), inspection=inspection)
        return {"status": "FAILED", "job_id": job_id, "error_code": "MODEL_UNAVAILABLE", "error_message": str(exc)}

    try:
        damage_type_map = await ensure_damage_types(db)

        run_ids: list[str] = []
        detection_ids: list[uuid.UUID] = []
        media_failures: list[dict[str, Any]] = []
        backends: set[str] = set()
        total_inference_ms = 0.0

        for media in media_items:
            item_start = utc_now()
            try:
                local_file = resolve_media(media)
                analysis = analyze_media_file(
                    local_file, media.media_type, detector, confidence_threshold, iou_threshold
                )
            except MediaValidationError as mve:
                logger.warning("Media %s of job %s rejected: %s", media.id, job_id, mve)
                media_failures.append({"media_id": str(media.id), "error_code": mve.code, "error_message": str(mve)})
                continue

            run, ids = await persist_media_analysis(
                db, job, media, inspection, analysis, confidence_threshold, item_start, damage_type_map
            )
            run_ids.append(str(run.id))
            detection_ids.extend(ids)
            backends.add(analysis.backend)
            total_inference_ms += analysis.inference_time_ms

        summary = {
            "processing_run_ids": run_ids,
            "media_total": len(media_items),
            "media_processed": len(run_ids),
            "media_failed": media_failures,
            "detection_count": len(detection_ids),
            "inference_duration_ms": round(total_inference_ms, 2),
            "inference_backends": sorted(backends),
        }

        if not run_ids:
            first = media_failures[0]
            await _mark_job_failed(
                db, job, first["error_code"],
                f"All {len(media_items)} media item(s) failed: {first['error_message']}",
                {**summary, "status": "FAILED"}, inspection=inspection,
            )
            return {"status": "FAILED", "job_id": job_id, "error_code": first["error_code"], **summary}

        job.status = "COMPLETED"
        job.completed_at = utc_now()
        job.result_metadata = {**summary, "status": "COMPLETED"}
        inspection.status = "ANALYZED"
        inspection.updated_at = utc_now()
        await db.commit()

        logger.info(
            "Inspection %s analyzed under job %s: %d/%d media, %d detections.",
            inspection_id, job_id, len(run_ids), len(media_items), len(detection_ids),
        )
        return {"status": "COMPLETED", "job_id": job_id, "detection_ids": detection_ids, **summary}

    except Exception as e:
        await db.rollback()
        await _mark_job_failed(
            db, job, "INFERENCE_ERROR", f"Inference pipeline error: {e!s}", inspection=inspection
        )
        logger.exception("Job %s failed with unexpected error", job_id)
        return {"status": "FAILED", "job_id": job_id, "error_code": "INFERENCE_ERROR", "error_message": str(e)}
