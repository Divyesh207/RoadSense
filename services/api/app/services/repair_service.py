import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.damage import DamageRecord
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.repair import RepairEvidence, RepairVerification
from app.schemas.repair import (
    RepairEvidenceCompleteRequest,
    RepairEvidenceUploadUrlRequest,
    RepairEvidenceUploadUrlResponse,
    RepairVerificationSubmitRequest,
)
from app.services.road_lifecycle import refresh_after_damage_change
from app.services.storage import (
    StorageError,
    StorageObjectNotFoundError,
    get_storage_backend,
    safe_filename,
    storage_http_exception,
    validate_object_key,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance in meters between two lat/lon coordinates."""
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


async def get_verified_job(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> MaintenanceJob:
    """Retrieve maintenance job with tenant isolation check."""
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job not found."},
        )
    return job


async def generate_evidence_upload_url(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    payload: RepairEvidenceUploadUrlRequest,
) -> RepairEvidenceUploadUrlResponse:
    await get_verified_job(db, maintenance_job_id, organization_id)

    bucket = settings.SUPABASE_STORAGE_BUCKET_REPAIR_EVIDENCE
    storage_path = f"{repair_evidence_prefix(maintenance_job_id)}{uuid.uuid4()}_{safe_filename(payload.filename)}"
    try:
        signed = await run_in_threadpool(
            lambda: get_storage_backend().create_signed_upload(bucket, storage_path, payload.content_type)
        )
    except StorageError as exc:
        raise storage_http_exception(exc) from exc

    return RepairEvidenceUploadUrlResponse(
        upload_url=signed.upload_url,
        storage_path=signed.path,
        storage_bucket=signed.bucket,
        expires_in_seconds=signed.expires_in,
        upload_method=signed.method,
        upload_headers=signed.headers,
    )


def repair_evidence_prefix(maintenance_job_id: uuid.UUID) -> str:
    return f"{maintenance_job_id}/"


async def complete_repair_evidence(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: RepairEvidenceCompleteRequest,
) -> RepairEvidence:
    job = await get_verified_job(db, maintenance_job_id, organization_id)

    # Only objects issued by upload-url for this job may be registered as evidence.
    if (
        payload.storage_bucket != settings.SUPABASE_STORAGE_BUCKET_REPAIR_EVIDENCE
        or not payload.storage_path.startswith(repair_evidence_prefix(maintenance_job_id))
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "INVALID_STORAGE_PATH",
                "message": "storage_bucket/storage_path must be the values issued by repair-evidence/upload-url for this job.",
            },
        )
    try:
        validate_object_key(payload.storage_bucket, payload.storage_path)
        # The object must actually have been uploaded; a failed upload is never registered.
        await run_in_threadpool(
            lambda: get_storage_backend().create_signed_download_url(payload.storage_bucket, payload.storage_path, 60)
        )
    except StorageObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "UPLOAD_NOT_FOUND", "message": "Upload the file to the signed URL before completing it."},
        ) from exc
    except StorageError as exc:
        raise storage_http_exception(exc) from exc
    if payload.media_type == "IMAGE" and not payload.mime_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_MEDIA_TYPE", "message": "IMAGE evidence must have an image/* MIME type."},
        )

    location_geom = None
    if payload.latitude is not None and payload.longitude is not None:
        location_geom = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)

    evidence = RepairEvidence(
        id=uuid.uuid4(),
        organization_id=organization_id,
        maintenance_job_id=maintenance_job_id,
        uploaded_by_user_id=user_id,
        evidence_type=payload.evidence_type,
        storage_bucket=payload.storage_bucket,
        storage_path=payload.storage_path,
        media_type=payload.media_type,
        mime_type=payload.mime_type,
        file_size_bytes=payload.file_size_bytes,
        checksum=payload.checksum,
        captured_at=payload.captured_at or utc_now(),
        location=location_geom,
        notes=payload.notes,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(evidence)

    # After-repair evidence on a COMPLETED job moves it to VERIFICATION_PENDING.
    if job.status == "COMPLETED" and payload.evidence_type == "AFTER_REPAIR":
        old_status = job.status
        job.status = "VERIFICATION_PENDING"
        job.updated_at = utc_now()
        hist = MaintenanceStatusHistory(
            id=uuid.uuid4(),
            organization_id=organization_id,
            maintenance_job_id=maintenance_job_id,
            previous_status=old_status,
            new_status="VERIFICATION_PENDING",
            changed_by_user_id=user_id,
            reason="Repair evidence uploaded; verification pending.",
            changed_at=utc_now(),
        )
        db.add(hist)

    await db.commit()
    await db.refresh(evidence)
    return evidence


async def list_job_evidence(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> list[RepairEvidence]:
    await get_verified_job(db, maintenance_job_id, organization_id)

    query = (
        select(RepairEvidence)
        .where(
            RepairEvidence.maintenance_job_id == maintenance_job_id,
            RepairEvidence.organization_id == organization_id,
        )
        .order_by(RepairEvidence.created_at.asc())
    )
    return list((await db.execute(query)).scalars().all())


async def run_ai_repair_verification(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    evidence_ids: list[uuid.UUID] | None = None,
) -> RepairVerification:
    """Run automated evidence checks on uploaded repair evidence vs the linked damage records.

    Checks only that after-repair evidence exists and where it was captured. No image
    analysis is performed (before/after image comparison is not implemented yet), so the
    result is never VERIFIED: final sign-off is always a human decision.
    """
    await get_verified_job(db, maintenance_job_id, organization_id)

    # Fetch evidence
    ev_query = select(RepairEvidence).where(
        RepairEvidence.maintenance_job_id == maintenance_job_id,
        RepairEvidence.organization_id == organization_id,
    )
    if evidence_ids:
        ev_query = ev_query.where(RepairEvidence.id.in_(evidence_ids))
    evidence_list = list((await db.execute(ev_query)).scalars().all())

    if not evidence_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "NO_EVIDENCE_FOUND",
                "message": "Cannot perform AI verification without uploaded repair evidence.",
            },
        )

    # Fetch linked damage records
    dmg_query = (
        select(DamageRecord)
        .join(MaintenanceDamageLink, MaintenanceDamageLink.damage_record_id == DamageRecord.id)
        .where(
            MaintenanceDamageLink.maintenance_job_id == maintenance_job_id,
            DamageRecord.organization_id == organization_id,
        )
    )
    damages = list((await db.execute(dmg_query)).scalars().all())

    # Automated evidence check (no image analysis). It only establishes whether
    # after-repair evidence exists and whether it was captured near the recorded
    # damage. It cannot judge repair quality and never marks a repair as verified;
    # that remains a human decision (submit_human_verification).
    after_evidence = [e for e in evidence_list if e.evidence_type == "AFTER_REPAIR"]
    damages_with_location = [d for d in damages if d.location is not None]

    distances_m: list[float] = []
    after_with_coords = 0
    for ev in after_evidence:
        if ev.location is None:
            continue
        try:
            pt_ev = to_shape(ev.location)
        except (AttributeError, ValueError, TypeError):
            continue
        after_with_coords += 1
        for dmg in damages_with_location:
            try:
                pt_dmg = to_shape(dmg.location)
            except (AttributeError, ValueError, TypeError):
                continue
            distances_m.append(haversine_distance_meters(pt_ev.y, pt_ev.x, pt_dmg.y, pt_dmg.x))
    min_dist_m = min(distances_m) if distances_m else None

    reasons: list[str] = []
    if not after_evidence:
        check_result = "REVIEW_REQUIRED"
        reasons.append("No after-repair evidence has been uploaded.")
    elif min_dist_m is None:
        # Previously this case was reported as VERIFIED; without coordinates on both
        # sides the location cannot be checked at all.
        check_result = "REVIEW_REQUIRED"
        if after_with_coords == 0:
            reasons.append("After-repair evidence has no GPS coordinates; location could not be checked.")
        if not damages_with_location:
            reasons.append("Linked damage records have no location; location could not be checked.")
    elif min_dist_m <= 25.0:
        check_result = "LOCATION_CONSISTENT"
        reasons.append(f"After-repair evidence was captured {min_dist_m:.1f} m from the recorded damage.")
    elif min_dist_m <= 50.0:
        check_result = "LOCATION_UNCERTAIN"
        reasons.append(f"Closest after-repair evidence is {min_dist_m:.1f} m from the recorded damage.")
    else:
        check_result = "LOCATION_MISMATCH"
        reasons.append(f"Closest after-repair evidence is {min_dist_m:.1f} m away (> 50 m) from the recorded damage.")

    findings: dict[str, Any] = {
        "check_type": "AUTOMATED_EVIDENCE_CHECK",
        "check_result": check_result,
        "reasons": reasons,
        "image_comparison_performed": False,
        "human_review_required": True,
        "evidence_analyzed_count": len(evidence_list),
        "after_repair_evidence_count": len(after_evidence),
        "damage_records_evaluated": len(damages),
        "closest_evidence_distance_meters": round(min_dist_m, 2) if min_dist_m is not None else None,
        "summary": (
            "Automated check of evidence presence and capture location only. No before/after image "
            "comparison was performed; repair quality must be confirmed by a reviewer."
        ),
    }

    # Only measured values; no image-derived scores exist yet.
    metrics: dict[str, Any] = {
        "closest_after_evidence_distance_meters": round(min_dist_m, 2) if min_dist_m is not None else None,
        "after_evidence_with_coordinates": after_with_coords,
        "damage_records_with_location": len(damages_with_location),
    }

    verification = RepairVerification(
        id=uuid.uuid4(),
        organization_id=organization_id,
        maintenance_job_id=maintenance_job_id,
        ai_processing_run_id=None,
        verified_by_user_id=None,
        verification_status="AUTOMATED_CHECK",
        verification_type="AUTOMATED_EVIDENCE_CHECK",
        ai_confidence=None,  # no model ran; a confidence value would be fabricated
        comparison_metrics=metrics,
        findings=findings,
        reviewer_notes=f"Automated evidence check (no image analysis): {check_result}. " + " ".join(reasons),
        verified_at=None,  # Not verified until a human decides
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    return verification


async def submit_human_verification(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: RepairVerificationSubmitRequest,
) -> RepairVerification:
    """Submit human review decision on repair verification.
    
    Transitions the maintenance job to VERIFIED or REJECTED,
    and updates linked damage records accordingly.
    """
    job = await get_verified_job(db, maintenance_job_id, organization_id)

    if job.status not in ["COMPLETED", "VERIFICATION_PENDING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_JOB_STATE",
                "message": f"Job in status '{job.status}' cannot be verified. Must be in COMPLETED or VERIFICATION_PENDING.",
            },
        )

    # Fetch linked damage records
    dmg_query = (
        select(DamageRecord)
        .join(MaintenanceDamageLink, MaintenanceDamageLink.damage_record_id == DamageRecord.id)
        .where(
            MaintenanceDamageLink.maintenance_job_id == maintenance_job_id,
            DamageRecord.organization_id == organization_id,
        )
    )
    damages = list((await db.execute(dmg_query)).scalars().all())

    # Create Verification record
    now = utc_now()
    verification = RepairVerification(
        id=uuid.uuid4(),
        organization_id=organization_id,
        maintenance_job_id=maintenance_job_id,
        ai_processing_run_id=None,
        verified_by_user_id=user_id,
        verification_status=payload.decision,
        verification_type="HUMAN_SIGNOFF",
        result="SUCCESSFUL" if payload.decision == "VERIFIED" else "SUBSTANDARD",
        ai_confidence=None,
        comparison_metrics=None,
        findings={"human_decision": payload.decision, "damages_updated": len(damages)},
        reviewer_notes=payload.notes,
        verified_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(verification)

    # Transition job status
    old_status = job.status
    job.status = payload.decision
    if payload.decision == "VERIFIED":
        job.verified_at = now
        for dmg in damages:
            dmg.status = "REPAIRED"
            dmg.updated_at = now
    else:  # REJECTED
        for dmg in damages:
            dmg.status = "CONFIRMED"  # Reopens damage as confirmed pending rework
            dmg.updated_at = now

    job.updated_at = now

    # Record status transition history
    hist = MaintenanceStatusHistory(
        id=uuid.uuid4(),
        organization_id=organization_id,
        maintenance_job_id=maintenance_job_id,
        previous_status=old_status,
        new_status=payload.decision,
        changed_by_user_id=user_id,
        reason=payload.notes or f"Repair verification {payload.decision.lower()} by authorized reviewer.",
        changed_at=now,
    )
    db.add(hist)

    await db.commit()
    await db.refresh(verification)
    # Repaired damage leaves the health count; rejected rework returns it.
    await refresh_after_damage_change(db, organization_id, damages)
    return verification


async def list_job_verifications(
    db: AsyncSession,
    maintenance_job_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> list[RepairVerification]:
    await get_verified_job(db, maintenance_job_id, organization_id)

    query = (
        select(RepairVerification)
        .where(
            RepairVerification.maintenance_job_id == maintenance_job_id,
            RepairVerification.organization_id == organization_id,
        )
        .order_by(desc(RepairVerification.created_at))
    )
    return list((await db.execute(query)).scalars().all())
