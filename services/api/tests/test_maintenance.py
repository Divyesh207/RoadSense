import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
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
async def seeded_maintenance_context(db_session):
    now = datetime.now(UTC)

    # 1. Road & Segment
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="State Highway 42",
        road_code="SH-42",
        road_type="STATE_HIGHWAY",
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
        name="SH42-KM0-KM2",
        start_chainage=0.0,
        end_chainage=2.0,
        length_meters=2000.0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(seg)

    # 2. Inspection
    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        inspector_user_id=uuid.UUID("a3333333-3333-3333-3333-333333333333"),
        notes="Spring Maintenance Survey",
        status="COMPLETED",
        captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db_session.add(insp)

    # 3. Damage Type
    dt = (await db_session.execute(select(DamageType).where(DamageType.code == "POTHOLE"))).scalar_one()

    # 4. Confirmed Damages
    dmg_crit = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=dt.id,
        source_type="AI",
        severity="CRITICAL",
        severity_score=92.5,
        status="CONFIRMED",
        location=WKTElement("POINT(73.8567 18.5204)", srid=4326),
        created_at=now,
        updated_at=now,
    )
    dmg_high = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=dt.id,
        source_type="AI",
        severity="HIGH",
        severity_score=75.0,
        status="CONFIRMED",
        location=WKTElement("POINT(73.8570 18.5210)", srid=4326),
        created_at=now,
        updated_at=now,
    )
    db_session.add_all([dmg_crit, dmg_high])
    await db_session.commit()

    return {
        "road": road,
        "segment": seg,
        "inspection": insp,
        "damage_crit": dmg_crit,
        "damage_high": dmg_high,
    }


@pytest.mark.asyncio
async def test_create_maintenance_job_unlinked(async_client, seeded_maintenance_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_maintenance_context

    payload = {
        "road_id": str(ctx["road"].id),
        "road_segment_id": str(ctx["segment"].id),
        "title": "Routine shoulder re-grading",
        "description": "Grade and compact road shoulder.",
        "priority": "LOW",
        "target_date": "2026-11-15",
    }

    resp = await async_client.post("/api/v1/maintenance-jobs", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["title"] == "Routine shoulder re-grading"
    assert data["status"] == "OPEN"
    assert data["priority_level"] == "LOW"
    assert data["damage_count"] == 0

    # History should have 1 entry
    job_id = data["id"]
    hist_resp = await async_client.get(f"/api/v1/maintenance-jobs/{job_id}/history", headers=headers)
    assert hist_resp.status_code == 200
    hist = hist_resp.json()["data"]
    assert len(hist) == 1
    assert hist[0]["new_status"] == "OPEN"


@pytest.mark.asyncio
async def test_create_maintenance_job_with_damages(async_client, seeded_maintenance_context, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_maintenance_context

    payload = {
        "road_id": str(ctx["road"].id),
        "road_segment_id": str(ctx["segment"].id),
        "title": "Emergency pothole repair",
        "damage_record_ids": [str(ctx["damage_crit"].id), str(ctx["damage_high"].id)],
    }

    resp = await async_client.post("/api/v1/maintenance-jobs", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["title"] == "Emergency pothole repair"
    assert data["status"] == "OPEN"
    # Auto-calculated priority from critical damage
    assert data["priority_level"] == "CRITICAL"
    assert data["priority_score"] >= 85.0
    assert data["damage_count"] == 2

    # Check that damage status transitioned to MAINTENANCE_SCHEDULED
    d1 = await db_session.get(DamageRecord, ctx["damage_crit"].id)
    assert d1.status == "MAINTENANCE_SCHEDULED"


@pytest.mark.asyncio
async def test_get_maintenance_job_and_list_filtering(async_client, seeded_maintenance_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    # Create 2 jobs
    await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={"title": "Job Alpha", "priority": "HIGH"},
    )
    resp2 = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={"title": "Job Beta", "priority": "LOW"},
    )
    job2_id = resp2.json()["data"]["id"]

    # Filter by priority=HIGH
    list_resp = await async_client.get("/api/v1/maintenance-jobs?priority=HIGH", headers=headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    assert all(item["priority_level"] == "HIGH" for item in items)

    # Get single job details
    get_resp = await async_client.get(f"/api/v1/maintenance-jobs/{job2_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["title"] == "Job Beta"


@pytest.mark.asyncio
async def test_patch_maintenance_job(async_client, seeded_maintenance_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={"title": "Initial Title", "priority": "MEDIUM"},
    )
    job_id = create_resp.json()["data"]["id"]

    patch_resp = await async_client.patch(
        f"/api/v1/maintenance-jobs/{job_id}",
        headers=headers,
        json={"title": "Updated Title", "description": "New description details"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["title"] == "Updated Title"
    assert patch_resp.json()["data"]["description"] == "New description details"


@pytest.mark.asyncio
async def test_assign_maintenance_job(async_client, seeded_maintenance_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={"title": "Patch crack sealing", "priority": "MEDIUM"},
    )
    job_id = create_resp.json()["data"]["id"]
    assert create_resp.json()["data"]["status"] == "OPEN"

    # Assign to crew lead
    assign_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/assign",
        headers=headers,
        json={"assigned_to": str(CREW_USER_ID)},
    )
    assert assign_resp.status_code == 200
    data = assign_resp.json()["data"]
    assert data["status"] == "ASSIGNED"
    assert data["assigned_to_user_id"] == str(CREW_USER_ID)


@pytest.mark.asyncio
async def test_maintenance_lifecycle_state_machine(async_client, seeded_maintenance_context, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_maintenance_context

    # Create job linked to critical damage
    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={
            "title": "Road resurfacing",
            "damage_record_ids": [str(ctx["damage_crit"].id)],
        },
    )
    job_id = create_resp.json()["data"]["id"]
    assert create_resp.json()["data"]["status"] == "OPEN"

    # 1. Invalid jump: OPEN -> VERIFIED (should fail with 400)
    inv_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "VERIFIED"},
    )
    assert inv_resp.status_code == 400
    assert inv_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # 2. OPEN -> ASSIGNED
    s1 = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "ASSIGNED", "notes": "Assigned to North Crew"},
    )
    assert s1.status_code == 200
    assert s1.json()["data"]["status"] == "ASSIGNED"

    # 3. ASSIGNED -> IN_PROGRESS
    s2 = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "IN_PROGRESS", "notes": "Work on site initiated"},
    )
    assert s2.status_code == 200
    assert s2.json()["data"]["status"] == "IN_PROGRESS"
    assert s2.json()["data"]["started_at"] is not None

    # Verify damage record also moved to IN_PROGRESS
    d = await db_session.get(DamageRecord, ctx["damage_crit"].id)
    assert d.status == "IN_PROGRESS"

    # 4. IN_PROGRESS -> COMPLETED
    s3 = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "COMPLETED", "notes": "Bitumen patch completed and compacted"},
    )
    assert s3.status_code == 200
    assert s3.json()["data"]["status"] == "COMPLETED"
    assert s3.json()["data"]["completed_at"] is not None

    # 5. COMPLETED -> VERIFICATION_PENDING
    s4 = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "VERIFICATION_PENDING", "notes": "Awaiting QA inspection"},
    )
    assert s4.status_code == 200
    assert s4.json()["data"]["status"] == "VERIFICATION_PENDING"

    # 6. VERIFICATION_PENDING -> VERIFIED
    s5 = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=headers,
        json={"status": "VERIFIED", "notes": "Patch visually verified and road reopened"},
    )
    assert s5.status_code == 200
    assert s5.json()["data"]["status"] == "VERIFIED"
    assert s5.json()["data"]["verified_at"] is not None

    # Verify damage record moved to REPAIRED
    await db_session.refresh(d)
    assert d.status == "REPAIRED"

    # Check complete history
    h_resp = await async_client.get(f"/api/v1/maintenance-jobs/{job_id}/history", headers=headers)
    assert h_resp.status_code == 200
    transitions = [h["new_status"] for h in h_resp.json()["data"]]
    assert transitions == ["OPEN", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "VERIFICATION_PENDING", "VERIFIED"]


@pytest.mark.asyncio
async def test_link_damages_to_existing_job(async_client, seeded_maintenance_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    ctx = seeded_maintenance_context

    # Create job without damages
    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers,
        json={"title": "General repairs"},
    )
    job_id = create_resp.json()["data"]["id"]

    # Link damage
    link_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/damages",
        headers=headers,
        json={"damage_record_id": str(ctx["damage_high"].id), "relationship_type": "PRIMARY"},
    )
    assert link_resp.status_code == 201
    assert link_resp.json()["data"]["damage_record_id"] == str(ctx["damage_high"].id)

    # Get linked damages
    get_damages_resp = await async_client.get(f"/api/v1/maintenance-jobs/{job_id}/damages", headers=headers)
    assert get_damages_resp.status_code == 200
    damages = get_damages_resp.json()["data"]
    assert len(damages) == 1
    assert damages[0]["damage_record_id"] == str(ctx["damage_high"].id)


@pytest.mark.asyncio
async def test_maintenance_multi_tenant_isolation(async_client, seeded_maintenance_context):
    token_org1 = await get_token_for(async_client)
    headers_org1 = {"Authorization": f"Bearer {token_org1}", "X-Organization-ID": str(ORG_1_ID)}

    # Create job in Org 1
    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=headers_org1,
        json={"title": "Org 1 Internal Job"},
    )
    job_id = create_resp.json()["data"]["id"]

    # Org 2 user cannot read Org 1 job
    token_org2 = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    headers_org2 = {"Authorization": f"Bearer {token_org2}", "X-Organization-ID": str(ORG_2_ID)}

    resp = await async_client.get(f"/api/v1/maintenance-jobs/{job_id}", headers=headers_org2)
    assert resp.status_code == 404

    # Org 2 user listing jobs should NOT include Org 1 jobs
    list_resp = await async_client.get("/api/v1/maintenance-jobs", headers=headers_org2)
    assert list_resp.status_code == 200
    org2_job_ids = [j["id"] for j in list_resp.json()["data"]]
    assert job_id not in org2_job_ids


@pytest.mark.asyncio
async def test_maintenance_rbac_permissions(async_client, seeded_maintenance_context):
    # Inspector lacks maintenance:create
    insp_token = await get_inspector_token(async_client)
    insp_headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}

    create_resp = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=insp_headers,
        json={"title": "Unauthorized job"},
    )
    assert create_resp.status_code == 403
    assert create_resp.json()["error"]["code"] == "FORBIDDEN"

    # Authority can create job
    auth_token = await get_token_for(async_client)
    auth_headers = {"Authorization": f"Bearer {auth_token}", "X-Organization-ID": str(ORG_1_ID)}
    create_resp2 = await async_client.post(
        "/api/v1/maintenance-jobs",
        headers=auth_headers,
        json={"title": "Authorized job"},
    )
    assert create_resp2.status_code == 201
    job_id = create_resp2.json()["data"]["id"]

    # Assign to crew lead
    await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/assign",
        headers=auth_headers,
        json={"assigned_to": str(CREW_USER_ID)},
    )

    # Crew has maintenance:status_update, so crew can advance job to IN_PROGRESS
    crew_token = await get_crew_token(async_client)
    crew_headers = {"Authorization": f"Bearer {crew_token}", "X-Organization-ID": str(ORG_1_ID)}
    status_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status",
        headers=crew_headers,
        json={"status": "IN_PROGRESS", "notes": "Crew started road patch"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "IN_PROGRESS"
