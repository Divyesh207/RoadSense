import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from inference.detector import DetectionResult
from inference.model_registry import ModelRegistry
from postprocessing.nms import RawDetection, suppress_temporal_duplicates
from postprocessing.severity import assess_damage_severity
from postprocessing.spatial import associate_detection_location
from preprocessing.image import preprocess_image
from preprocessing.validator import MediaValidationError, validate_media_file
from preprocessing.video import sample_video_frames
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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


async def ensure_ai_model(db: AsyncSession, model_id_name: str = "road-damage-yolo-v8", version: str = "1.0.0") -> uuid.UUID:
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
        name=info.name if info else model_id_name,
        model_family=info.model_family if info else "YOLO",
        model_type=info.model_type if info else "OBJECT_DETECTION",
        version=version,
        artifact_uri=info.artifact_uri if info else f"local://models/{model_id_name}.pt",
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
    Executes the full AI pipeline on an inspection media item:
    1. Updates ProcessingJob to RUNNING
    2. Validates media
    3. Runs OpenCV preprocessing and YOLO detection
    4. Applies NMS and severity assessment
    5. Creates AIProcessingRun and AIDetection records
    6. Updates ProcessingJob to COMPLETED (or FAILED on error)
    """
    from app.models.ai import AIDetection, AIProcessingRun
    from app.models.inspection import Inspection, InspectionMedia
    from app.models.jobs import ProcessingJob
    from app.services.spatial import point_to_wkt, wkt_or_geom_to_point

    t_start = utc_now()

    # 1. Fetch job and media
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
        job.status = "FAILED"
        job.error_message = f"InspectionMedia {media_id} not found"
        job.completed_at = utc_now()
        await db.commit()
        raise ValueError(job.error_message)

    # Fetch parent inspection for GPS and Road association
    insp_stmt = select(Inspection).where(Inspection.id == media.inspection_id)
    inspection = (await db.execute(insp_stmt)).scalar_one_or_none()

    # Determine file path
    target_file = Path(file_path) if file_path else Path(media.storage_path)

    try:
        # 2. Media Validation
        validation = validate_media_file(target_file, expected_type=media.media_type)

        # 3. Model setup
        model_uuid = await ensure_ai_model(db)
        damage_type_map = await ensure_damage_types(db)
        registry = ModelRegistry()
        detector = registry.get_detector()

        detections_to_persist: list[tuple[RawDetection, dict[str, Any]]] = []
        total_inference_time_ms = 0.0

        if validation.media_type == "IMAGE":
            # Image Preprocessing & Inference
            prep = preprocess_image(str(target_file))
            det_result: DetectionResult = detector.detect(
                prep.original_image,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
            )
            total_inference_time_ms += det_result.inference_time_ms

            for det in det_result.detections:
                severity_eval = assess_damage_severity(
                    damage_type_code=det.damage_type_code,
                    bbox_x_min=det.bbox_x_min,
                    bbox_y_min=det.bbox_y_min,
                    bbox_x_max=det.bbox_x_max,
                    bbox_y_max=det.bbox_y_max,
                    pixel_width=prep.orig_width,
                    pixel_height=prep.orig_height,
                )
                detections_to_persist.append((det, severity_eval.__dict__))

        elif validation.media_type == "VIDEO":
            # Video Frame Extraction & Inference
            all_frame_detections: list[RawDetection] = []
            for frame_obj in sample_video_frames(target_file, sample_fps=1.0, max_frames=60):
                det_result = detector.detect(
                    frame_obj.image,
                    confidence_threshold=confidence_threshold,
                    iou_threshold=iou_threshold,
                    frame_number=frame_obj.frame_number,
                    frame_timestamp_ms=frame_obj.timestamp_ms,
                )
                total_inference_time_ms += det_result.inference_time_ms
                all_frame_detections.extend(det_result.detections)

            # Suppress temporal duplicates across video frames
            deduped_video_detections = suppress_temporal_duplicates(all_frame_detections)
            for det in deduped_video_detections:
                severity_eval = assess_damage_severity(
                    damage_type_code=det.damage_type_code,
                    bbox_x_min=det.bbox_x_min,
                    bbox_y_min=det.bbox_y_min,
                    bbox_x_max=det.bbox_x_max,
                    bbox_y_max=det.bbox_y_max,
                    pixel_width=validation.width_px,
                    pixel_height=validation.height_px,
                )
                detections_to_persist.append((det, severity_eval.__dict__))

        # 4. Create AIProcessingRun
        t_comp = utc_now()
        run = AIProcessingRun(
            id=uuid.uuid4(),
            organization_id=organization_id,
            processing_job_id=job.id,
            model_id=model_uuid,
            inspection_id=media.inspection_id,
            media_id=media.id,
            run_type="INSPECTION_DETECTION",
            configuration_version="1.0.0",
            confidence_threshold=confidence_threshold,
            input_metadata={
                "media_type": validation.media_type,
                "mime_type": validation.mime_type,
                "dimensions": [validation.width_px, validation.height_px],
                "file_size": validation.file_size_bytes,
            },
            output_metadata={
                "detection_count": len(detections_to_persist),
                "inference_time_ms": total_inference_time_ms,
                "model_version": "1.0.0",
            },
            status="COMPLETED",
            started_at=t_start,
            completed_at=t_comp,
            created_at=t_start,
        )
        db.add(run)
        await db.flush()

        # 5. Extract GPS from parent inspection
        insp_coords = wkt_or_geom_to_point(inspection.location) if inspection else None
        insp_lat = insp_coords[0] if insp_coords else None
        insp_lon = insp_coords[1] if insp_coords else None

        geo_assoc = associate_detection_location(
            detection_lat=insp_lat,
            detection_lon=insp_lon,
            fallback_road_id=inspection.road_id if inspection else None,
            fallback_segment_id=inspection.road_segment_id if inspection else None,
        )

        pt_geom = point_to_wkt(insp_lat, insp_lon) if (insp_lat and insp_lon) else None

        # 6. Persist AIDetection records
        persisted_detection_ids = []
        for det, sev_data in detections_to_persist:
            dt_id = damage_type_map.get(det.damage_type_code) or damage_type_map.get("OTHER")
            ai_det = AIDetection(
                id=uuid.uuid4(),
                organization_id=organization_id,
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
                    "geospatial_association": geo_assoc.__dict__,
                    "metadata": det.metadata,
                },
                created_at=t_comp,
            )
            db.add(ai_det)
            persisted_detection_ids.append(ai_det.id)

        # 7. Update ProcessingJob to COMPLETED
        job.status = "COMPLETED"
        job.completed_at = t_comp
        job.result_metadata = {
            "processing_run_id": str(run.id),
            "detection_count": len(persisted_detection_ids),
            "inference_duration_ms": total_inference_time_ms,
            "status": "COMPLETED",
        }
        await db.commit()

        logger.info(
            f"AI Pipeline completed for job {job_id}, run {run.id}: "
            f"{len(persisted_detection_ids)} detections persisted."
        )

        return {
            "status": "COMPLETED",
            "job_id": job.id,
            "run_id": run.id,
            "detection_count": len(persisted_detection_ids),
            "detection_ids": persisted_detection_ids,
        }

    except MediaValidationError as mve:
        await db.rollback()
        job.status = "FAILED"
        job.completed_at = utc_now()
        job.failed_at = utc_now()
        job.error_code = mve.code
        job.error_message = f"Validation failed ({mve.code}): {mve!s}"
        job.result_metadata = {"error_code": mve.code, "error_details": mve.details}
        await db.commit()
        logger.error(f"Job {job_id} failed media validation: {mve}")
        return {
            "status": "FAILED",
            "job_id": job.id,
            "error_code": mve.code,
            "error_message": str(mve),
        }

    except Exception as e:
        await db.rollback()
        job.status = "FAILED"
        job.completed_at = utc_now()
        job.failed_at = utc_now()
        job.error_code = "INFERENCE_ERROR"
        job.error_message = f"Inference pipeline error: {e!s}"
        await db.commit()
        logger.exception("Job %s failed with unexpected error", job_id)
        return {
            "status": "FAILED",
            "job_id": job.id,
            "error_message": str(e),
        }
