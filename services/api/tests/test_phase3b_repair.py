# ruff: noqa: F811  (pytest fixture imported from test_repair_verification and used as an argument)
"""Phase 3B: evidence upload through signed storage, queued image verification (idempotent),
human review provenance, assignment validation and job context.

The worker's image analysis itself is tested in services/ai-worker; here the worker's
completion is simulated by writing the result the worker would store."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.models.damage import DamageRecord
from app.models.history import AuditLog
from app.models.inspection import InspectionMedia
from app.models.jobs import ProcessingJob
from app.models.maintenance import MaintenanceJob, MaintenanceStatusHistory
from app.models.repair import RepairVerification
from tests.conftest import CREW_USER_ID, ORG_1_ID, OTHER_ORG_USER_ID
from tests.test_repair_verification import (  # noqa: F401
    get_inspector_token,
    get_token_for,
    seeded_repair_context,
)

JPEG = b"\xff\xd8\xff\xe0synthetic-test-bytes"


@pytest.fixture
def dispatched(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.services.repair_verification_service.dispatch_repair_verification",
        lambda job_id, ver_id, org_id: sent.append((job_id, ver_id, org_id)) or str(job_id),
    )
    return sent


async def headers(async_client):
    return {"Authorization": f"Bearer {await get_token_for(async_client)}", "X-Organization-ID": str(ORG_1_ID)}


async def upload_evidence(async_client, h, job_id, evidence_type, data=JPEG, content_type="image/jpeg"):
    """Real flow: signed upload URL -> PUT bytes -> complete."""
    up = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/upload-url", headers=h,
        json={"filename": f"{evidence_type.lower()}.jpg", "content_type": content_type, "size_bytes": len(data),
              "evidence_type": evidence_type},
    )
    assert up.status_code == 200, up.text
    u = up.json()["data"]
    put = await async_client.put("/api/v1" + u["upload_url"].split("/api/v1", 1)[1], content=data,
                                 headers=u["upload_headers"])
    assert put.status_code in (200, 201), put.text
    done = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete", headers=h,
        json={"storage_path": u["storage_path"], "storage_bucket": u["storage_bucket"], "evidence_type": evidence_type,
              "media_type": "IMAGE", "mime_type": content_type, "file_size_bytes": len(data)},
    )
    assert done.status_code == 201, done.text
    return done.json()["data"]


async def queue(async_client, h, job_id, body=None):
    return await async_client.post(f"/api/v1/maintenance-jobs/{job_id}/repair-verifications", headers=h, json=body or {})


async def simulate_worker(db_session, ver_id, result="SUCCESSFUL"):
    ver = await db_session.get(RepairVerification, uuid.UUID(ver_id))
    await db_session.refresh(ver)
    ver.verification_status, ver.result = "COMPLETED", result
    ver.model_name, ver.model_version, ver.algorithm_version = "rdd2022-india-yolo11s", "india-v1", "repair-cv-v1.0.1"
    ver.findings = {"result": result, "reason_code": "TEST"}
    pjob = await db_session.get(ProcessingJob, ver.processing_job_id)
    pjob.status = "COMPLETED"
    await db_session.commit()
    return ver


# --- evidence upload ------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_evidence_uploads_are_rejected(async_client, seeded_repair_context):
    h = await headers(async_client)
    job_id = seeded_repair_context["job"].id
    url = f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/upload-url"
    bad_type = await async_client.post(url, headers=h, json={"filename": "x.pdf", "content_type": "application/pdf",
                                                              "size_bytes": 10})
    assert bad_type.status_code == 422
    too_big = await async_client.post(url, headers=h, json={"filename": "x.jpg", "content_type": "image/jpeg",
                                                             "size_bytes": 25 * 1024 * 1024})
    assert too_big.status_code == 422
    # Completing an object that was never uploaded must fail (failed upload is not registered).
    not_uploaded = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete", headers=h,
        json={"storage_path": f"{job_id}/never-uploaded.jpg", "evidence_type": "AFTER_REPAIR"},
    )
    assert not_uploaded.status_code == 422
    assert not_uploaded.json()["error"]["code"] == "UPLOAD_NOT_FOUND"
    wrong_mime = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete", headers=h,
        json={"storage_path": f"{job_id}/a.jpg", "evidence_type": "AFTER_REPAIR", "mime_type": "text/plain"},
    )
    assert wrong_mime.status_code == 422


@pytest.mark.asyncio
async def test_signed_download_urls_for_evidence(async_client, seeded_repair_context, dispatched):
    h = await headers(async_client)
    job_id = seeded_repair_context["job"].id
    before = await upload_evidence(async_client, h, job_id, "BEFORE_REPAIR")
    after = await upload_evidence(async_client, h, job_id, "AFTER_REPAIR")
    dl = await async_client.get(f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/{after['id']}/download-url", headers=h)
    assert dl.status_code == 200
    assert "signature=" in dl.json()["data"]["download_url"]
    ver = (await queue(async_client, h, job_id)).json()["data"]
    urls = (await async_client.get(
        f"/api/v1/maintenance-jobs/{job_id}/repair-verifications/{ver['id']}/image-urls", headers=h
    )).json()["data"]
    assert urls["before_source"] == "REPAIR_EVIDENCE_BEFORE"
    assert before["storage_path"].split("/")[-1] in urls["before_url"]
    assert after["storage_path"].split("/")[-1] in urls["after_url"]


# --- queueing -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queue_is_idempotent_per_image_pair(async_client, db_session, seeded_repair_context, dispatched):
    h = await headers(async_client)
    job_id = seeded_repair_context["job"].id
    before = await upload_evidence(async_client, h, job_id, "BEFORE_REPAIR")
    after = await upload_evidence(async_client, h, job_id, "AFTER_REPAIR")

    first = await queue(async_client, h, job_id)
    assert first.status_code == 202, first.text
    ver = first.json()["data"]
    assert ver["verification_type"] == "AUTOMATED_IMAGE_ANALYSIS" and ver["verification_status"] == "QUEUED"
    assert ver["before_evidence_id"] == before["id"] and ver["after_evidence_id"] == after["id"]
    assert ver["result"] is None and ver["ai_confidence"] is None

    second = await queue(async_client, h, job_id)
    assert second.status_code == 200
    assert second.json()["data"]["id"] == ver["id"]
    assert len(dispatched) == 1
    assert await db_session.scalar(select(func.count(RepairVerification.id))) == 1
    assert await db_session.scalar(
        select(func.count(ProcessingJob.id)).where(ProcessingJob.job_type == "REPAIR_VERIFICATION")
    ) == 1
    job = await db_session.get(MaintenanceJob, job_id)
    await db_session.refresh(job)
    assert job.status == "VERIFICATION_PENDING"


@pytest.mark.asyncio
async def test_failed_job_is_requeued_without_duplicates(async_client, db_session, seeded_repair_context, dispatched):
    h = await headers(async_client)
    job_id = seeded_repair_context["job"].id
    await upload_evidence(async_client, h, job_id, "BEFORE_REPAIR")
    await upload_evidence(async_client, h, job_id, "AFTER_REPAIR")
    ver = (await queue(async_client, h, job_id)).json()["data"]
    pjob = await db_session.get(ProcessingJob, uuid.UUID(ver["processing_job_id"]))
    await db_session.refresh(pjob)
    pjob.status, pjob.attempts, pjob.error_code = "FAILED", 3, "STORAGE_UNAVAILABLE"
    await db_session.commit()

    again = await queue(async_client, h, job_id)
    assert again.status_code == 202
    assert again.json()["data"]["id"] == ver["id"]
    assert again.json()["data"]["verification_status"] == "QUEUED"
    await db_session.refresh(pjob)
    assert pjob.status == "QUEUED" and pjob.attempts == 0
    assert len(dispatched) == 2
    assert await db_session.scalar(select(func.count(RepairVerification.id))) == 1


@pytest.mark.asyncio
async def test_queue_preconditions(async_client, db_session, seeded_repair_context, dispatched):
    h = await headers(async_client)
    job = seeded_repair_context["job"]
    no_after = await queue(async_client, h, job.id)
    assert no_after.status_code == 400 and no_after.json()["error"]["code"] == "NO_AFTER_EVIDENCE"
    after = await upload_evidence(async_client, h, job.id, "AFTER_REPAIR")
    no_before = await queue(async_client, h, job.id)
    assert no_before.json()["error"]["code"] == "NO_BEFORE_IMAGE"
    wrong_kind = await queue(async_client, h, job.id, {"before_evidence_id": after["id"]})
    assert wrong_kind.json()["error"]["code"] == "INVALID_EVIDENCE"
    db_job = await db_session.get(MaintenanceJob, job.id)
    db_job.status = "OPEN"
    await db_session.commit()
    open_job = await queue(async_client, h, job.id)
    assert open_job.status_code == 400 and open_job.json()["error"]["code"] == "INVALID_JOB_STATE"
    assert dispatched == []


@pytest.mark.asyncio
async def test_inspection_photo_is_used_when_no_before_evidence(async_client, db_session, seeded_repair_context, dispatched):
    h = await headers(async_client)
    ctx = seeded_repair_context
    media = InspectionMedia(
        id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id, media_type="IMAGE",
        storage_bucket="inspection-media", storage_path=f"inspections/{ctx['inspection'].id}/p.jpg",
        mime_type="image/jpeg", upload_status="COMPLETED", created_at=datetime.now(UTC),
    )
    db_session.add(media)
    await db_session.commit()
    await upload_evidence(async_client, h, ctx["job"].id, "AFTER_REPAIR")
    ver = (await queue(async_client, h, ctx["job"].id)).json()["data"]
    assert ver["before_media_id"] == str(media.id) and ver["before_evidence_id"] is None


@pytest.mark.asyncio
async def test_dispatch_failure_reports_503_and_marks_failed(async_client, db_session, seeded_repair_context, monkeypatch):
    from app.core.task_queue import TaskDispatchError

    def down(*_):
        raise TaskDispatchError("broker down")

    monkeypatch.setattr("app.services.repair_verification_service.dispatch_repair_verification", down)
    h = await headers(async_client)
    job_id = seeded_repair_context["job"].id
    await upload_evidence(async_client, h, job_id, "BEFORE_REPAIR")
    await upload_evidence(async_client, h, job_id, "AFTER_REPAIR")
    resp = await queue(async_client, h, job_id)
    assert resp.status_code == 503
    ver = (await db_session.execute(select(RepairVerification))).scalar_one()
    await db_session.refresh(ver)
    assert ver.verification_status == "FAILED" and ver.result is None


# --- human review ---------------------------------------------------------------------------


async def queued_verification(async_client, db_session, ctx, result):
    h = await headers(async_client)
    await upload_evidence(async_client, h, ctx["job"].id, "BEFORE_REPAIR")
    await upload_evidence(async_client, h, ctx["job"].id, "AFTER_REPAIR")
    ver = (await queue(async_client, h, ctx["job"].id)).json()["data"]
    await simulate_worker(db_session, ver["id"], result)
    return h, ver


async def review(async_client, h, job_id, ver_id, body):
    return await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-verifications/{ver_id}/review", headers=h, json=body
    )


@pytest.mark.asyncio
async def test_confirmed_successful_review_verifies_job_and_keeps_automated_result(
    async_client, db_session, seeded_repair_context, dispatched
):
    ctx = seeded_repair_context
    h, ver = await queued_verification(async_client, db_session, ctx, "SUCCESSFUL")
    resp = await review(async_client, h, ctx["job"].id, ver["id"], {"decision": "CONFIRMED", "notes": "Patch looks sound"})
    assert resp.status_code == 201, resp.text
    r = resp.json()["data"]
    assert r["verification_type"] == "HUMAN_REVIEW" and r["review_decision"] == "CONFIRMED"
    assert (r["previous_result"], r["result"]) == ("SUCCESSFUL", "SUCCESSFUL")
    assert r["reviewed_verification_id"] == ver["id"]
    assert r["verified_by_user_id"] is not None and r["verified_at"] is not None
    assert (r["model_name"], r["model_version"]) == ("rdd2022-india-yolo11s", "india-v1")

    auto = await db_session.get(RepairVerification, uuid.UUID(ver["id"]))
    await db_session.refresh(auto)
    assert (auto.verification_status, auto.result, auto.verified_by_user_id) == ("COMPLETED", "SUCCESSFUL", None)
    job = await db_session.get(MaintenanceJob, ctx["job"].id)
    await db_session.refresh(job)
    assert job.status == "VERIFIED" and job.verified_at is not None
    dmg = await db_session.get(DamageRecord, ctx["damage"].id)
    await db_session.refresh(dmg)
    assert dmg.status == "REPAIRED"
    hist = (await db_session.execute(select(MaintenanceStatusHistory).where(
        MaintenanceStatusHistory.maintenance_job_id == job.id, MaintenanceStatusHistory.new_status == "VERIFIED"
    ))).scalars().all()
    assert len(hist) == 1
    audit = (await db_session.execute(select(AuditLog).where(AuditLog.action == "REPAIR_VERIFICATION_REVIEWED"))).scalar_one()
    assert audit.before_data["automated_result"] == "SUCCESSFUL" and audit.after_data["final_result"] == "SUCCESSFUL"

    # Job is closed: no second decision.
    again = await review(async_client, h, ctx["job"].id, ver["id"], {"decision": "UNRESOLVED"})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_rejecting_result_requires_outcome_and_notes(async_client, db_session, seeded_repair_context, dispatched):
    ctx = seeded_repair_context
    h, ver = await queued_verification(async_client, db_session, ctx, "SUCCESSFUL")
    no_notes = await review(async_client, h, ctx["job"].id, ver["id"], {"decision": "REJECTED", "final_result": "SUBSTANDARD"})
    assert no_notes.status_code == 422
    same = await review(async_client, h, ctx["job"].id, ver["id"],
                        {"decision": "REJECTED", "final_result": "SUCCESSFUL", "notes": "x"})
    assert same.status_code == 422
    ok = await review(async_client, h, ctx["job"].id, ver["id"],
                      {"decision": "REJECTED", "final_result": "SUBSTANDARD", "notes": "Edge cracks remain at patch border"})
    assert ok.status_code == 201
    assert (ok.json()["data"]["previous_result"], ok.json()["data"]["result"]) == ("SUCCESSFUL", "SUBSTANDARD")
    job = await db_session.get(MaintenanceJob, ctx["job"].id)
    await db_session.refresh(job)
    assert job.status == "REJECTED"
    dmg = await db_session.get(DamageRecord, ctx["damage"].id)
    await db_session.refresh(dmg)
    assert dmg.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_unresolved_review_keeps_job_pending(async_client, db_session, seeded_repair_context, dispatched):
    ctx = seeded_repair_context
    h, ver = await queued_verification(async_client, db_session, ctx, "UNRESOLVED")
    resp = await review(async_client, h, ctx["job"].id, ver["id"], {"decision": "UNRESOLVED", "notes": "Need closer photo"})
    assert resp.status_code == 201
    assert resp.json()["data"]["result"] == "UNRESOLVED"
    job = await db_session.get(MaintenanceJob, ctx["job"].id)
    await db_session.refresh(job)
    assert job.status == "VERIFICATION_PENDING" and job.verified_at is None
    dmg = await db_session.get(DamageRecord, ctx["damage"].id)
    await db_session.refresh(dmg)
    assert dmg.status == "MAINTENANCE_SCHEDULED"


@pytest.mark.asyncio
async def test_review_needs_completed_analysis_and_permission(async_client, db_session, seeded_repair_context, dispatched):
    ctx = seeded_repair_context
    h = await headers(async_client)
    await upload_evidence(async_client, h, ctx["job"].id, "BEFORE_REPAIR")
    await upload_evidence(async_client, h, ctx["job"].id, "AFTER_REPAIR")
    ver = (await queue(async_client, h, ctx["job"].id)).json()["data"]
    pending = await review(async_client, h, ctx["job"].id, ver["id"], {"decision": "CONFIRMED"})
    assert pending.status_code == 400 and pending.json()["error"]["code"] == "VERIFICATION_NOT_REVIEWABLE"
    await simulate_worker(db_session, ver["id"], "SUCCESSFUL")
    insp_h = {"Authorization": f"Bearer {await get_inspector_token(async_client)}", "X-Organization-ID": str(ORG_1_ID)}
    forbidden = await review(async_client, insp_h, ctx["job"].id, ver["id"], {"decision": "CONFIRMED"})
    assert forbidden.status_code == 403


# --- maintenance workflow -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_transition_rejected(async_client, seeded_repair_context):
    h = await headers(async_client)
    resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{seeded_repair_context['job'].id}/status", headers=h, json={"status": "ASSIGNED"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_assignees_and_assignment_validation(async_client, seeded_repair_context):
    h = await headers(async_client)
    resp = await async_client.get("/api/v1/maintenance-jobs/assignees", headers=h)
    assert resp.status_code == 200, resp.text
    users = resp.json()["data"]["users"]
    assert str(CREW_USER_ID) in {u["id"] for u in users}
    assert str(OTHER_ORG_USER_ID) not in {u["id"] for u in users}

    job_id = seeded_repair_context["job"].id
    outsider = await async_client.post(f"/api/v1/maintenance-jobs/{job_id}/assign", headers=h,
                                       json={"assigned_to_user_id": str(OTHER_ORG_USER_ID)})
    assert outsider.status_code == 400 and outsider.json()["error"]["code"] == "INVALID_ASSIGNEE"
    fake_org = await async_client.post(f"/api/v1/maintenance-jobs/{job_id}/assign", headers=h,
                                       json={"assigned_to_organization_id": str(uuid.uuid4())})
    assert fake_org.status_code == 400 and fake_org.json()["error"]["code"] == "INVALID_CONTRACTOR"
    ok = await async_client.post(f"/api/v1/maintenance-jobs/{job_id}/assign", headers=h,
                                 json={"assigned_to_user_id": str(CREW_USER_ID)})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_job_context_links_damage_inspection_road_and_segment(async_client, seeded_repair_context):
    h = await headers(async_client)
    ctx = seeded_repair_context
    resp = await async_client.get(f"/api/v1/maintenance-jobs/{ctx['job'].id}/context", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["road"]["name"] == "Expressway 101"
    assert data["segment"]["segment_number"] == 1
    assert data["damages"][0]["id"] == str(ctx["damage"].id)
    assert data["damages"][0]["inspection_id"] == str(ctx["inspection"].id)
    assert data["damages"][0]["severity"] == "HIGH"
    assert data["assigned_user"]["id"] == str(CREW_USER_ID)
    assert data["allowed_transitions"] == ["VERIFICATION_PENDING", "IN_PROGRESS"]


@pytest.mark.asyncio
async def test_damage_in_maintenance_workflow_serializes(async_client, db_session, seeded_repair_context):
    """Damage linked to a job is MAINTENANCE_SCHEDULED / IN_PROGRESS; reading it must not fail."""
    h = await headers(async_client)
    dmg_id = seeded_repair_context["damage"].id
    for state in ("MAINTENANCE_SCHEDULED", "IN_PROGRESS"):
        dmg = await db_session.get(DamageRecord, dmg_id)
        dmg.status = state
        await db_session.commit()
        resp = await async_client.get(f"/api/v1/damages/{dmg_id}", headers=h)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == state
