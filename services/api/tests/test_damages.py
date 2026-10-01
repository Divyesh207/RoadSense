import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from app.models.ai import AIDetection, DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection, InspectionMedia
from app.models.road import Road
from app.services.spatial import point_to_wkt
from sqlalchemy import select

from tests.conftest import (
    AUTHORITY_USER_ID,
    INSPECTOR_USER_ID,
    ORG_1_ID,
    ORG_2_ID,
)


async def get_token_for(async_client, email="authority@example.com", password="AuthoritySecret123!"):
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


async def get_inspector_token(async_client):
    return await get_token_for(async_client, "inspector@example.com", "InspectorSecret123!")


@pytest_asyncio.fixture
async def seeded_damage_context(db_session):
    # Fetch damage types
    types = (await db_session.execute(select(DamageType))).scalars().all()
    type_map = {t.code: t.id for t in types}

    # Create Road
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="MG Road",
        road_code="MG-001",
        road_type="URBAN",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(road)

    # Create Inspection
    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspector_user_id=INSPECTOR_USER_ID,
        road_id=road.id,
        status="COMPLETED",
        source="API",
        location=point_to_wkt(18.5204, 73.8567),
        gps_accuracy_meters=4.0,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(insp)

    # Create Media
    media = InspectionMedia(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        media_type="IMAGE",
        storage_bucket="inspection-media",
        storage_path="org/insp/road.jpg",
        original_filename="road.jpg",
        mime_type="image/jpeg",
        file_size_bytes=102400,
        upload_status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(media)
    await db_session.commit()

    return {
        "type_map": type_map,
        "road": road,
        "inspection": insp,
        "media": media,
    }


@pytest.mark.asyncio
async def test_list_damage_types(async_client):
    resp = await async_client.get("/api/v1/damage-types")
    assert resp.status_code == 200
    types = resp.json()["data"]
    codes = [t["code"] for t in types]
    assert "POTHOLE" in codes
    assert "CRACK" in codes
    assert "DEPRESSION" in codes


@pytest.mark.asyncio
async def test_create_manual_damage_record(async_client, seeded_damage_context):
    token = await get_inspector_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    ctx = seeded_damage_context
    payload = {
        "inspection_id": str(ctx["inspection"].id),
        "damage_type_id": str(ctx["type_map"]["POTHOLE"]),
        "severity": "HIGH",
        "location": {"latitude": 18.5210, "longitude": 73.8570},
        "road_id": str(ctx["road"].id),
        "estimated_area_m2": 1.25,
        "notes": "Large open pothole in right lane",
    }

    resp = await async_client.post("/api/v1/damages", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["severity"] == "HIGH"
    assert data["status"] == "CONFIRMED"
    assert data["source_type"] == "MANUAL"
    assert data["damage_type_code"] == "POTHOLE"
    assert data["estimated_area_m2"] == 1.25


@pytest.mark.asyncio
async def test_create_damage_from_ai_detection(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # 1. Insert raw AI Detection
    det_id = uuid.uuid4()
    run_id = uuid.uuid4()
    det = AIDetection(
        id=det_id,
        organization_id=ORG_1_ID,
        ai_processing_run_id=run_id,
        inspection_id=ctx["inspection"].id,
        media_id=ctx["media"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        confidence=0.92,
        bbox_x_min=0.20,
        bbox_y_min=0.30,
        bbox_x_max=0.50,
        bbox_y_max=0.60,
        pixel_width=640,
        pixel_height=480,
        location=point_to_wkt(18.5204, 73.8567),
        raw_output={"severity_assessment": {"severity": "HIGH", "score": 0.78}},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(det)
    await db_session.commit()

    # 2. Promote to canonical candidate damage record
    resp = await async_client.post(f"/api/v1/damages/from-detection/{det_id}", headers=headers)
    assert resp.status_code == 201
    dmg = resp.json()["data"]
    assert dmg["source_detection_id"] == str(det_id)
    assert dmg["status"] == "PENDING_REVIEW"
    assert dmg["source_type"] == "AI"
    assert dmg["severity"] == "HIGH"
    assert dmg["confidence"] == 0.92


@pytest.mark.asyncio
async def test_list_damages_with_filters(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create sample damage records
    d1 = DamageRecord(
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        severity="CRITICAL",
        status="CONFIRMED",
        created_at=datetime.now(timezone.utc),
    )
    d2 = DamageRecord(
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["CRACK"],
        severity="LOW",
        status="PENDING_REVIEW",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([d1, d2])
    await db_session.commit()

    # Filter by severity
    resp_crit = await async_client.get("/api/v1/damages?severity=CRITICAL", headers=headers)
    assert resp_crit.status_code == 200
    items = resp_crit.json()["data"]
    assert len(items) >= 1
    assert all(i["severity"] == "CRITICAL" for i in items)

    # Filter by status
    resp_pend = await async_client.get("/api/v1/damages?status=PENDING_REVIEW", headers=headers)
    assert resp_pend.status_code == 200
    assert any(i["status"] == "PENDING_REVIEW" for i in resp_pend.json()["data"])


@pytest.mark.asyncio
async def test_get_and_update_damage_record(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    dmg_id = uuid.uuid4()
    dmg = DamageRecord(
        id=dmg_id,
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        severity="MEDIUM",
        status="PENDING_REVIEW",
        notes="Initial notes",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg)
    await db_session.commit()

    # Get single
    resp_get = await async_client.get(f"/api/v1/damages/{dmg_id}", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["data"]["id"] == str(dmg_id)

    # Patch update
    resp_patch = await async_client.patch(
        f"/api/v1/damages/{dmg_id}",
        json={"notes": "Updated damage notes", "estimated_area_m2": 2.5},
        headers=headers,
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["data"]["notes"] == "Updated damage notes"
    assert resp_patch.json()["data"]["estimated_area_m2"] == 2.5


@pytest.mark.asyncio
async def test_human_review_confirm_workflow(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)  # Authority user has damage_records:review
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    dmg_id = uuid.uuid4()
    dmg = DamageRecord(
        id=dmg_id,
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        severity="MEDIUM",
        status="PENDING_REVIEW",
        confidence=0.75,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg)
    await db_session.commit()

    # Perform review: Confirm and escalate to CRITICAL
    review_payload = {
        "decision": "CONFIRMED",
        "severity": "CRITICAL",
        "notes": "Verified in person. Deep pothole requiring urgent cold mix patch.",
    }
    resp_rev = await async_client.post(f"/api/v1/damages/{dmg_id}/review", json=review_payload, headers=headers)
    assert resp_rev.status_code == 200
    updated_dmg = resp_rev.json()["data"]
    assert updated_dmg["status"] == "CONFIRMED"
    assert updated_dmg["severity"] == "CRITICAL"
    assert updated_dmg["reviewed_by_user_id"] == str(AUTHORITY_USER_ID)
    assert updated_dmg["reviewed_at"] is not None

    # Verify audit history
    resp_history = await async_client.get(f"/api/v1/damages/{dmg_id}/reviews", headers=headers)
    assert resp_history.status_code == 200
    history = resp_history.json()["data"]
    assert len(history) == 1
    assert history[0]["review_status"] == "CONFIRMED"
    assert history[0]["original_severity"] == "MEDIUM"
    assert history[0]["reviewed_severity"] == "CRITICAL"
    assert "Verified in person" in history[0]["review_notes"]


@pytest.mark.asyncio
async def test_human_review_reject_workflow(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    dmg_id = uuid.uuid4()
    dmg = DamageRecord(
        id=dmg_id,
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["CRACK"],
        severity="LOW",
        status="PENDING_REVIEW",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg)
    await db_session.commit()

    review_payload = {
        "decision": "REJECTED",
        "notes": "False detection. Shadow from tree canopy.",
    }
    resp_rev = await async_client.post(f"/api/v1/damages/{dmg_id}/review", json=review_payload, headers=headers)
    assert resp_rev.status_code == 200
    assert resp_rev.json()["data"]["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_get_inspection_detections_endpoint(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    run_id = uuid.uuid4()
    det = AIDetection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        ai_processing_run_id=run_id,
        inspection_id=ctx["inspection"].id,
        media_id=ctx["media"].id,
        damage_type_id=ctx["type_map"]["CRACK"],
        confidence=0.88,
        bbox_x_min=0.1,
        bbox_y_min=0.1,
        bbox_x_max=0.4,
        bbox_y_max=0.4,
        raw_output={"severity_assessment": {"severity": "LOW"}},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(det)
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/inspections/{ctx['inspection'].id}/detections", headers=headers)
    assert resp.status_code == 200
    dets = resp.json()["data"]
    assert len(dets) >= 1
    assert dets[0]["damage_type"] == "CRACK"
    assert dets[0]["confidence"] == 0.88


@pytest.mark.asyncio
async def test_damage_multi_tenant_isolation(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    # Org 1 token
    token_org1 = await get_token_for(async_client)

    # Damage belongs to Org 2
    dmg_org2 = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_2_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        severity="HIGH",
        status="PENDING_REVIEW",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg_org2)
    await db_session.commit()

    headers_org1 = {"Authorization": f"Bearer {token_org1}", "X-Organization-ID": str(ORG_1_ID)}

    # Org 1 should not see Org 2 damage
    resp_get = await async_client.get(f"/api/v1/damages/{dmg_org2.id}", headers=headers_org1)
    assert resp_get.status_code == 404

    # Org 1 cannot review Org 2 damage
    resp_rev = await async_client.post(
        f"/api/v1/damages/{dmg_org2.id}/review",
        json={"decision": "CONFIRMED"},
        headers=headers_org1,
    )
    assert resp_rev.status_code == 404


@pytest.mark.asyncio
async def test_damage_rbac_permissions(async_client, db_session, seeded_damage_context):
    ctx = seeded_damage_context
    token_inspector = await get_inspector_token(async_client)
    headers = {"Authorization": f"Bearer {token_inspector}", "X-Organization-ID": str(ORG_1_ID)}

    dmg = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=ctx["inspection"].id,
        damage_type_id=ctx["type_map"]["POTHOLE"],
        severity="MEDIUM",
        status="PENDING_REVIEW",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg)
    await db_session.commit()

    # Inspector does NOT have damage_records:review permission
    resp = await async_client.post(
        f"/api/v1/damages/{dmg.id}/review",
        json={"decision": "CONFIRMED"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
