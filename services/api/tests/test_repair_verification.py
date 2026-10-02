import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.road import Road, RoadSegment
from tests.conftest import CREW_USER_ID, ORG_1_ID, ORG_2_ID


async def get_token_for(async_client, email="authority@example.com", password="AuthoritySecret123!"):
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


async def get_crew_token(async_client):
    return await get_token_for(async_client, "crew@example.com", "CrewSecret123!")


async def get_inspector_token(async_client):
    return await get_token_for(async_client, "inspector@example.com", "InspectorSecret123!")


@pytest_asyncio.fixture
async def seeded_repair_context(db_session):
    now = datetime.now(timezone.utc)

    # Road & Segment
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="Expressway 101",
        road_code="EXP-101",
        road_type="EXPRESSWAY",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(road)

    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="EXP101-SEC1",
        start_chainage=0.0,
        end_chainage=5.0,
        length_meters=5000.0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(seg)

    # Inspection
    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        inspector_user_id=uuid.UUID("a3333333-3333-3333-3333-333333333333"),
        notes="Pre-repair baseline inspection",
        status="COMPLETED",
        captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(insp)

    # Damage Type
    dt = (await db_session.execute(select(DamageType).where(DamageType.code == "POTHOLE"))).scalar_one()

    # Confirmed Damage
    dmg = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=dt.id,
        source_type="AI",
        severity="HIGH",
        severity_score=78.0,
        status="MAINTENANCE_SCHEDULED",
        location=WKTElement("POINT(73.8567 18.5204)", srid=4326),
        created_at=now,
        updated_at=now,
    )
    db_session.add(dmg)

    # Maintenance Job in COMPLETED status
    job = MaintenanceJob(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        created_by_user_id=uuid.UUID("a2222222-2222-2222-2222-222222222222"),
        assigned_to_user_id=CREW_USER_ID,
        title="Bitumen patch on EXP-101",
        priority_level="HIGH",
        priority_score=78.0,
        status="COMPLETED",
        location=WKTElement("POINT(73.8567 18.5204)", srid=4326),
        started_at=now,
        completed_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(job)

    link = MaintenanceDamageLink(
        maintenance_job_id=job.id,
        damage_record_id=dmg.id,
        relationship_type="PRIMARY",
        created_at=now,
    )
    db_session.add(link)
    await db_session.flush()

    return {
        "road": road,
        "segment": seg,
        "inspection": insp,
        "damage": dmg,
        "job": job,
        "link": link,
    }


@pytest.mark.asyncio
async def test_repair_evidence_upload_url(async_client, seeded_repair_context):
    token = await get_crew_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_repair_context
    job_id = ctx["job"].id

    payload = {
        "filename": "patch_finish.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 2048500,
        "evidence_type": "AFTER_REPAIR",
    }
    resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/upload-url",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert "upload_url" in data
    assert "patch_finish.jpg" in data["storage_path"]
    assert data["storage_bucket"] == "repair-evidence"


@pytest.mark.asyncio
async def test_repair_evidence_complete_and_list(async_client, seeded_repair_context, db_session):
    token = await get_crew_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_repair_context
    job_id = ctx["job"].id

    # Complete upload with GPS location close to damage (lat 18.5204, lon 73.8567)
    payload = {
        "storage_path": f"{job_id}/evidence_01.jpg",
        "storage_bucket": "repair-evidence",
        "evidence_type": "AFTER_REPAIR",
        "media_type": "IMAGE",
        "mime_type": "image/jpeg",
        "file_size_bytes": 1024000,
        "latitude": 18.52041,
        "longitude": 73.85672,
        "notes": "Pothole filled with HMA and rolled flush.",
    }
    resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete",
        headers=headers,
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["evidence_type"] == "AFTER_REPAIR"
    assert data["latitude"] is not None
    assert data["longitude"] is not None

    # Verify job status transitioned to VERIFICATION_PENDING
    job = await db_session.get(MaintenanceJob, job_id)
    assert job.status == "VERIFICATION_PENDING"

    # List evidence
    list_resp = await async_client.get(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence",
        headers=headers,
    )
    assert list_resp.status_code == 200
    ev_list = list_resp.json()["data"]
    assert len(ev_list) == 1
    assert ev_list[0]["storage_path"] == f"{job_id}/evidence_01.jpg"


@pytest.mark.asyncio
async def test_ai_repair_verification_eval(async_client, seeded_repair_context, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_repair_context
    job_id = ctx["job"].id

    # Upload after repair evidence
    ev_payload = {
        "storage_path": f"{job_id}/ai_eval_after.jpg",
        "evidence_type": "AFTER_REPAIR",
        "latitude": 18.520405,
        "longitude": 73.856705,
        "notes": "Flush asphalt overlay.",
    }
    await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete",
        headers=headers,
        json=ev_payload,
    )

    # Trigger AI verification evaluation
    eval_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/ai-verify",
        headers=headers,
        json={},
    )
    assert eval_resp.status_code == 200, eval_resp.text
    eval_data = eval_resp.json()["data"]
    assert eval_data["verification_status"] == "AI_EVALUATED"
    assert eval_data["ai_confidence"] is not None
    assert eval_data["ai_confidence"] >= 0.8
    assert eval_data["findings"]["ai_recommendation"] == "VERIFIED"
    assert eval_data["findings"]["residual_damage_detected"] is False

    # CRITICAL RULE: Job must NOT be auto-verified by AI evaluation alone!
    job = await db_session.get(MaintenanceJob, job_id)
    assert job.status == "VERIFICATION_PENDING"
    assert job.verified_at is None


@pytest.mark.asyncio
async def test_human_verification_workflow_verified(async_client, seeded_repair_context, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_repair_context
    job_id = ctx["job"].id
    damage_id = ctx["damage"].id

    # Add evidence first
    await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete",
        headers=headers,
        json={
            "storage_path": f"{job_id}/final_signoff.jpg",
            "evidence_type": "AFTER_REPAIR",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
    )

    # Road Authority signs off as VERIFIED
    verify_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/verify",
        headers=headers,
        json={
            "decision": "VERIFIED",
            "notes": "Visual review confirms smooth asphalt layer and no remaining defect.",
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    v_data = verify_resp.json()["data"]
    assert v_data["verification_status"] == "VERIFIED"
    assert v_data["reviewer_notes"] is not None

    db_session.expire_all()

    # Check job is now VERIFIED
    job = await db_session.get(MaintenanceJob, job_id)
    assert job.status == "VERIFIED"
    assert job.verified_at is not None

    # Check damage is now marked REPAIRED
    dmg = await db_session.get(DamageRecord, damage_id)
    assert dmg.status == "REPAIRED"

    # List verifications
    v_list_resp = await async_client.get(
        f"/api/v1/maintenance-jobs/{job_id}/verifications",
        headers=headers,
    )
    assert v_list_resp.status_code == 200
    assert len(v_list_resp.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_human_verification_workflow_rejected(async_client, seeded_repair_context, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_repair_context
    job_id = ctx["job"].id
    damage_id = ctx["damage"].id

    # Road Authority rejects verification
    verify_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/verify",
        headers=headers,
        json={
            "decision": "REJECTED",
            "notes": "Compaction inadequate; surface depression still visible.",
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["data"]["verification_status"] == "REJECTED"

    db_session.expire_all()

    # Job transitions to REJECTED
    job = await db_session.get(MaintenanceJob, job_id)
    assert job.status == "REJECTED"

    # Damage stays active / marked CONFIRMED for rework
    dmg = await db_session.get(DamageRecord, damage_id)
    assert dmg.status == "CONFIRMED"


@pytest.mark.asyncio
async def test_repair_verification_rbac_and_tenant_isolation(async_client, seeded_repair_context):
    ctx = seeded_repair_context
    job_id = ctx["job"].id

    # 1. Inspector lacks maintenance:verify
    insp_token = await get_inspector_token(async_client)
    insp_headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}

    unauth_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/verify",
        headers=insp_headers,
        json={"decision": "VERIFIED"},
    )
    assert unauth_resp.status_code == 403
    assert unauth_resp.json()["error"]["code"] == "FORBIDDEN"

    # 2. Org 2 user cannot access Org 1 repair evidence
    org2_token = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    org2_headers = {"Authorization": f"Bearer {org2_token}", "X-Organization-ID": str(ORG_2_ID)}

    notfound_resp = await async_client.get(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence",
        headers=org2_headers,
    )
    assert notfound_resp.status_code == 404
