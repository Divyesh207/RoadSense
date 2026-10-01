import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.repair import RepairVerification
from app.models.road import Road, RoadSegment
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from tests.conftest import CREW_USER_ID, ORG_1_ID, ORG_2_ID


async def get_token_for(async_client, email="authority@example.com", password="AuthoritySecret123!"):
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


async def get_crew_token(async_client):
    return await get_token_for(async_client, "crew@example.com", "CrewSecret123!")


@pytest_asyncio.fixture
async def seeded_recurrence_context(db_session):
    now = datetime.now(timezone.utc)
    t_past = now - timedelta(days=60)

    # Road & Segment
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="State Highway 42",
        road_code="SH-42",
        road_type="STATE_HIGHWAY",
        is_active=True,
        created_at=t_past,
        updated_at=t_past,
    )
    db_session.add(road)

    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="SH42-SEC1",
        start_chainage=0.0,
        end_chainage=10.0,
        length_meters=10000.0,
        is_active=True,
        created_at=t_past,
        updated_at=t_past,
    )
    db_session.add(seg)

    # Past Inspection
    past_insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        inspector_user_id=uuid.UUID("a3333333-3333-3333-3333-333333333333"),
        notes="Historical survey",
        status="COMPLETED",
        captured_at=t_past,
        created_at=t_past,
        updated_at=t_past,
    )
    db_session.add(past_insp)

    # Damage Type
    dt = (await db_session.execute(select(DamageType).where(DamageType.code == "POTHOLE"))).scalar_one()

    # Historical Damage
    hist_damage = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=past_insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=dt.id,
        source_type="AI",
        severity="HIGH",
        severity_score=82.0,
        status="REPAIRED",
        location=WKTElement("POINT(73.85670 18.52040)", srid=4326),
        detected_at=t_past,
        created_at=t_past,
        updated_at=t_past,
    )
    db_session.add(hist_damage)

    # Maintenance Job in the past
    t_repair = now - timedelta(days=45)
    job = MaintenanceJob(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        created_by_user_id=uuid.UUID("a2222222-2222-2222-2222-222222222222"),
        assigned_to_user_id=CREW_USER_ID,
        title="Repair Pothole at Ch 2.5",
        priority_level="HIGH",
        status="VERIFIED",
        location=WKTElement("POINT(73.85670 18.52040)", srid=4326),
        started_at=t_repair,
        completed_at=t_repair,
        verified_at=t_repair,
        created_at=t_repair,
        updated_at=t_repair,
    )
    db_session.add(job)

    link = MaintenanceDamageLink(
        maintenance_job_id=job.id,
        damage_record_id=hist_damage.id,
        relationship_type="PRIMARY",
        created_at=t_repair,
    )
    db_session.add(link)

    ver = RepairVerification(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        maintenance_job_id=job.id,
        verified_by_user_id=uuid.UUID("a2222222-2222-2222-2222-222222222222"),
        verification_status="VERIFIED",
        ai_confidence=0.91,
        reviewer_notes="Pothole filled and sealed cleanly.",
        verified_at=t_repair,
        created_at=t_repair,
        updated_at=t_repair,
    )
    db_session.add(ver)

    # New Inspection and Damage ~11 meters away, 45 days after repair
    new_insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        inspector_user_id=uuid.UUID("a3333333-3333-3333-3333-333333333333"),
        notes="Recent post-monsoon survey",
        status="COMPLETED",
        captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(new_insp)

    new_damage = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=new_insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=dt.id,
        source_type="AI",
        severity="MEDIUM",
        severity_score=65.0,
        status="DETECTED",
        # ~11 meters from 73.85670 18.52040
        location=WKTElement("POINT(73.85678 18.52045)", srid=4326),
        detected_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(new_damage)

    await db_session.flush()

    return {
        "road": road,
        "segment": seg,
        "hist_damage": hist_damage,
        "job": job,
        "verification": ver,
        "new_damage": new_damage,
    }


@pytest.mark.asyncio
async def test_recurrence_detection_and_matching(async_client, seeded_recurrence_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_recurrence_context
    new_dmg_id = ctx["new_damage"].id

    # 1. Evaluate recurrence for new damage
    eval_resp = await async_client.post(
        "/api/v1/recurrence/evaluate",
        headers=headers,
        json={"new_damage_id": str(new_dmg_id), "max_distance_meters": 30.0},
    )
    assert eval_resp.status_code == 200, eval_resp.text
    data = eval_resp.json()["data"]
    assert len(data) >= 1

    rec = data[0]
    assert rec["historical_damage_id"] == str(ctx["hist_damage"].id)
    assert rec["new_damage_id"] == str(new_dmg_id)
    assert rec["related_maintenance_job_id"] == str(ctx["job"].id)
    assert rec["related_repair_verification_id"] == str(ctx["verification"].id)
    assert rec["spatial_distance_meters"] is not None
    assert rec["spatial_distance_meters"] < 30.0
    assert rec["temporal_distance_days"] >= 40
    assert rec["similarity_score"] == 1.0  # Both are POTHOLE
    assert rec["recurrence_score"] > 0.5
    assert rec["status"] == "POTENTIAL"


@pytest.mark.asyncio
async def test_recurrence_list_and_get(async_client, seeded_recurrence_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_recurrence_context

    # Run evaluate first
    await async_client.post(
        "/api/v1/recurrence/evaluate",
        headers=headers,
        json={"new_damage_id": str(ctx["new_damage"].id)},
    )

    # List recurrences
    list_resp = await async_client.get(
        f"/api/v1/recurrence?road_segment_id={ctx['segment'].id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    res_data = list_resp.json()
    assert res_data["meta"]["total_count"] >= 1
    rec_item = res_data["data"][0]
    rec_id = rec_item["id"]

    # Get single recurrence record
    get_resp = await async_client.get(
        f"/api/v1/recurrence/{rec_id}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == rec_id


@pytest.mark.asyncio
async def test_recurrence_human_review(async_client, seeded_recurrence_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_recurrence_context

    # Run evaluate first
    eval_resp = await async_client.post(
        "/api/v1/recurrence/evaluate",
        headers=headers,
        json={"new_damage_id": str(ctx["new_damage"].id)},
    )
    rec_id = eval_resp.json()["data"][0]["id"]

    # Review as CONFIRMED
    review_resp = await async_client.post(
        f"/api/v1/recurrence/{rec_id}/review",
        headers=headers,
        json={
            "status": "CONFIRMED",
            "notes": "Base asphalt layer failure recurring in rainy season.",
        },
    )
    assert review_resp.status_code == 200, review_resp.text
    reviewed = review_resp.json()["data"]
    assert reviewed["status"] == "CONFIRMED"
    assert reviewed["review_notes"] == "Base asphalt layer failure recurring in rainy season."
    assert reviewed["reviewed_by_user_id"] is not None
    assert reviewed["reviewed_at"] is not None


@pytest.mark.asyncio
async def test_segment_historical_timeline(async_client, seeded_recurrence_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_recurrence_context
    seg_id = ctx["segment"].id

    # Evaluate recurrence
    await async_client.post(
        "/api/v1/recurrence/evaluate",
        headers=headers,
        json={"road_segment_id": str(seg_id)},
    )

    # Get timeline
    timeline_resp = await async_client.get(
        f"/api/v1/recurrence/segments/{seg_id}/timeline",
        headers=headers,
    )
    assert timeline_resp.status_code == 200, timeline_resp.text
    tl = timeline_resp.json()["data"]
    assert tl["road_segment_id"] == str(seg_id)
    assert tl["total_events"] >= 5

    event_types = [e["event_type"] for e in tl["events"]]
    assert "DAMAGE_DETECTED" in event_types
    assert "MAINTENANCE_CREATED" in event_types
    assert "MAINTENANCE_COMPLETED" in event_types
    assert "REPAIR_VERIFIED" in event_types
    assert "RECURRENCE_DETECTED" in event_types


@pytest.mark.asyncio
async def test_recurrence_rbac_and_tenant_isolation(async_client, seeded_recurrence_context):
    ctx = seeded_recurrence_context
    token = await get_token_for(async_client)
    headers_org1 = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    eval_resp = await async_client.post(
        "/api/v1/recurrence/evaluate",
        headers=headers_org1,
        json={"new_damage_id": str(ctx["new_damage"].id)},
    )
    rec_id = eval_resp.json()["data"][0]["id"]

    # 1. Crew lacks maintenance:verify permission for review
    crew_token = await get_crew_token(async_client)
    crew_headers = {"Authorization": f"Bearer {crew_token}", "X-Organization-ID": str(ORG_1_ID)}

    unauth_resp = await async_client.post(
        f"/api/v1/recurrence/{rec_id}/review",
        headers=crew_headers,
        json={"status": "CONFIRMED"},
    )
    assert unauth_resp.status_code == 403

    # 2. Other organization tenant isolation check
    other_token = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    headers_org2 = {"Authorization": f"Bearer {other_token}", "X-Organization-ID": str(ORG_2_ID)}
    not_found_resp = await async_client.get(
        f"/api/v1/recurrence/{rec_id}",
        headers=headers_org2,
    )
    assert not_found_resp.status_code == 404
