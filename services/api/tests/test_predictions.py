import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.models.intelligence import RoadHealthSnapshot
from app.models.road import Road, RoadSegment
from app.services.spatial import geojson_to_wkt, point_to_wkt
from tests.conftest import (
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
async def seeded_prediction_context(db_session):
    types = (await db_session.execute(select(DamageType))).scalars().all()
    type_map = {t.code: t.id for t in types}

    # Road
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="JM Road",
        road_code="JM-001",
        road_type="URBAN",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(road)

    # Segment
    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="JM Road Segment 1",
        start_chainage=0.0,
        end_chainage=1.0,
        length_meters=1000.0,
        geometry=geojson_to_wkt({"type": "LineString", "coordinates": [[73.8400, 18.5300], [73.8500, 18.5300]]}),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(seg)

    # Inspection
    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspector_user_id=INSPECTOR_USER_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        status="COMPLETED",
        source="API",
        location=point_to_wkt(18.5300, 73.8450),
        gps_accuracy_meters=4.0,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(insp)

    # Damage
    pothole_id = type_map.get("POTHOLE", next(iter(type_map.values())))
    dmg = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=pothole_id,
        source_type="AI",
        severity="HIGH",
        severity_score=75.0,
        status="CONFIRMED",
        confidence=0.90,
        location=point_to_wkt(18.5300, 73.8450),
        detected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(dmg)

    # Health snapshot
    health = RoadHealthSnapshot(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        health_score=70.0,
        health_status="FAIR",
        calculation_version="health-v1.0.0",
        factors={"damage_density": 1.0, "total_damages": 1},
        calculated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(health)
    await db_session.commit()

    return {
        "road": road,
        "segment": seg,
        "inspection": insp,
        "damage": dmg,
        "health": health,
    }


@pytest.mark.asyncio
async def test_prediction_insufficient_data(async_client, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Empty segment with no inspection or health snapshot
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="Empty Road For Pred",
        road_code="EMP-PRED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="No Data Seg",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([road, seg])
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/road-segments/{seg.id}/predictions",
        headers=headers,
        json={"prediction_horizon_days": 90},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "INSUFFICIENT_DATA"
    assert data["predicted_risk"] is None
    assert data["predicted_value"] is None
    assert data["confidence"] is None
    assert "Insufficient" in data["features"].get("reason", "")


@pytest.mark.asyncio
async def test_create_segment_prediction_success(async_client, seeded_prediction_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_prediction_context["segment"].id)

    resp = await async_client.post(
        f"/api/v1/road-segments/{seg_id}/predictions",
        headers=headers,
        json={"prediction_horizon_days": 180, "target_type": "DETERIORATION_RISK", "persist": True},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "GENERATED"
    assert data["prediction_horizon_days"] == 180
    assert data["model_name"] == "XGBoost-Road-Deterioration"
    assert data["predicted_risk"] is not None
    assert 0.0 <= data["predicted_risk"] <= 100.0
    assert data["predicted_value"] is not None
    assert data["uncertainty_lower"] is not None
    assert data["uncertainty_upper"] is not None
    assert data["confidence"] is not None
    assert 0.0 <= data["confidence"] <= 1.0
    assert "disclaimer" in data
    assert "must not be treated as guaranteed" in data["disclaimer"]


@pytest.mark.asyncio
async def test_get_segment_prediction_latest(async_client, seeded_prediction_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_prediction_context["segment"].id)

    # First get triggers on-demand prediction or retrieves latest
    resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/predictions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["road_segment_id"] == seg_id
    assert data["status"] == "GENERATED"
    assert data["model_name"] == "XGBoost-Road-Deterioration"


@pytest.mark.asyncio
async def test_prediction_history_pagination(async_client, seeded_prediction_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_prediction_context["segment"].id)

    # Generate 3 predictions with different horizons
    for horizon in [30, 90, 180]:
        resp = await async_client.post(
            f"/api/v1/road-segments/{seg_id}/predictions",
            headers=headers,
            json={"prediction_horizon_days": horizon},
        )
        assert resp.status_code == 200

    hist_resp = await async_client.get(
        f"/api/v1/road-segments/{seg_id}/predictions/history?page=1&page_size=2",
        headers=headers,
    )
    assert hist_resp.status_code == 200
    payload = hist_resp.json()
    assert len(payload["data"]) == 2
    assert payload["meta"]["total_count"] >= 3
    assert payload["meta"]["page"] == 1
    assert payload["meta"]["has_next"] is True


@pytest.mark.asyncio
async def test_prediction_multi_tenant_isolation(async_client, seeded_prediction_context):
    # Log in as Org 2 user
    token_org2 = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    headers_org2 = {"Authorization": f"Bearer {token_org2}", "X-Organization-ID": str(ORG_2_ID)}
    seg_id = str(seeded_prediction_context["segment"].id)

    # Org 2 cannot read Org 1 prediction
    resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/predictions", headers=headers_org2)
    assert resp.status_code == 404

    # Org 2 cannot read Org 1 prediction history
    hist_resp = await async_client.get(
        f"/api/v1/road-segments/{seg_id}/predictions/history",
        headers=headers_org2,
    )
    assert hist_resp.status_code == 404


@pytest.mark.asyncio
async def test_prediction_rbac_permissions(async_client, seeded_prediction_context):
    insp_token = await get_inspector_token(async_client)
    insp_headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_prediction_context["segment"].id)

    # Field inspector has predictions:read
    read_resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/predictions", headers=insp_headers)
    assert read_resp.status_code == 200

    # Field inspector lacks predictions:create
    create_resp = await async_client.post(
        f"/api/v1/road-segments/{seg_id}/predictions",
        headers=insp_headers,
        json={"prediction_horizon_days": 90},
    )
    assert create_resp.status_code == 403
    assert create_resp.json()["error"]["code"] == "FORBIDDEN"
