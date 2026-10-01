import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.models.road import Road, RoadSegment
from app.services.spatial import geojson_to_wkt, point_to_wkt
from sqlalchemy import select

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
async def seeded_gis_context(db_session):
    # Fetch damage types
    types = (await db_session.execute(select(DamageType))).scalars().all()
    type_map = {t.code: t.id for t in types}

    # Create Road
    road_geom = {
        "type": "LineString",
        "coordinates": [[73.8500, 18.5200], [73.8600, 18.5200]],
    }
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="FC Road",
        road_code="FC-001",
        road_type="URBAN",
        geometry=geojson_to_wkt(road_geom),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(road)

    # Create Segment
    seg_geom = {
        "type": "LineString",
        "coordinates": [[73.8500, 18.5200], [73.8550, 18.5200]],
    }
    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="FC Road Segment 1",
        start_chainage=0.0,
        end_chainage=0.5,
        length_meters=500.0,
        geometry=geojson_to_wkt(seg_geom),
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(seg)

    # Create Inspection
    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspector_user_id=INSPECTOR_USER_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        status="COMPLETED",
        source="API",
        location=point_to_wkt(18.5200, 73.8525),
        gps_accuracy_meters=3.5,
        captured_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(insp)

    # Create Damages: 1 Critical, 1 Medium
    pothole_id = type_map.get("POTHOLE", next(iter(type_map.values())))
    dmg1 = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=pothole_id,
        source_type="AI",
        severity="CRITICAL",
        severity_score=90.0,
        status="CONFIRMED",
        confidence=0.95,
        location=point_to_wkt(18.5200, 73.8520),
        detected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    dmg2 = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        road_id=road.id,
        road_segment_id=seg.id,
        damage_type_id=pothole_id,
        source_type="AI",
        severity="MEDIUM",
        severity_score=50.0,
        status="DETECTED",
        confidence=0.80,
        location=point_to_wkt(18.5200, 73.8530),
        detected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([dmg1, dmg2])
    await db_session.commit()

    return {
        "road": road,
        "segment": seg,
        "inspection": insp,
        "damages": [dmg1, dmg2],
        "type_map": type_map,
    }


@pytest.mark.asyncio
async def test_get_map_damages_endpoint(async_client, seeded_gis_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # 1. Fetch all damages
    resp = await async_client.get("/api/v1/map/damages", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 2

    # Check damage item structure
    item = next(d for d in data if d["id"] == str(seeded_gis_context["damages"][0].id))
    assert item["severity"] == "CRITICAL"
    assert item["status"] == "CONFIRMED"
    assert round(item["latitude"], 4) == 18.5200
    assert round(item["longitude"], 4) == 73.8520
    assert item["road_name"] == "FC Road"
    assert item["segment_number"] == 1

    # 2. Filter by severity
    resp_crit = await async_client.get("/api/v1/map/damages?severity=CRITICAL", headers=headers)
    assert resp_crit.status_code == 200
    crit_items = resp_crit.json()["data"]
    assert all(d["severity"] == "CRITICAL" for d in crit_items)

    # 3. Filter by spatial bounding box containing the point
    resp_bbox = await async_client.get(
        "/api/v1/map/damages?min_lat=18.51&min_lon=73.84&max_lat=18.53&max_lon=73.86",
        headers=headers,
    )
    assert resp_bbox.status_code == 200
    assert len(resp_bbox.json()["data"]) >= 2

    # 4. Filter by non-overlapping bounding box
    resp_outside = await async_client.get(
        "/api/v1/map/damages?min_lat=19.00&min_lon=74.00&max_lat=19.10&max_lon=74.10",
        headers=headers,
    )
    assert resp_outside.status_code == 200
    assert len(resp_outside.json()["data"]) == 0


@pytest.mark.asyncio
async def test_get_map_roads_and_segments(async_client, seeded_gis_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Map Roads
    resp_roads = await async_client.get("/api/v1/map/roads", headers=headers)
    assert resp_roads.status_code == 200
    roads = resp_roads.json()["data"]
    assert len(roads) >= 1
    road_item = next(r for r in roads if r["id"] == str(seeded_gis_context["road"].id))
    assert road_item["name"] == "FC Road"
    assert road_item["damage_count"] >= 2
    assert road_item["critical_damage_count"] >= 1
    assert road_item["geometry"]["type"] == "LineString"

    # Map Segments
    resp_segs = await async_client.get("/api/v1/map/segments", headers=headers)
    assert resp_segs.status_code == 200
    segs = resp_segs.json()["data"]
    assert len(segs) >= 1
    seg_item = next(s for s in segs if s["id"] == str(seeded_gis_context["segment"].id))
    assert seg_item["segment_number"] == 1
    assert seg_item["damage_count"] >= 2
    assert seg_item["critical_damage_count"] >= 1
    assert seg_item["geometry"]["type"] == "LineString"


@pytest.mark.asyncio
async def test_segment_health_calculation_and_factors(async_client, seeded_gis_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_gis_context["segment"].id)

    # Trigger calculation
    calc_resp = await async_client.post(
        f"/api/v1/road-segments/{seg_id}/calculate-health",
        headers=headers,
        json={"notes": "Automated test health calculation", "persist_snapshot": True},
    )
    assert calc_resp.status_code == 200
    data = calc_resp.json()["data"]
    assert data["road_segment_id"] == seg_id
    assert data["health_score"] is not None
    # Deductions: Critical 25, Medium 7 => 100 - 32 = 68.0
    assert data["health_score"] == 68.0
    assert data["health_status"] == "FAIR"
    assert data["calculation_version"] == "health-v1.0.0"
    assert data["factors"]["total_damages"] == 2
    assert data["factors"]["severity_breakdown"]["critical"] == 1
    assert data["factors"]["severity_breakdown"]["medium"] == 1

    # Fetch latest snapshot via GET
    get_resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/health", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["health_score"] == 68.0


@pytest.mark.asyncio
async def test_segment_health_insufficient_data(async_client, db_session):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create empty road and segment without inspections or damages
    empty_road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="Empty Road",
        road_code="EMP-001",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    empty_seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=empty_road.id,
        segment_number=1,
        name="Empty Segment 1",
        start_chainage=0.0,
        end_chainage=0.1,
        length_meters=100.0,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([empty_road, empty_seg])
    await db_session.commit()

    resp = await async_client.get(f"/api/v1/road-segments/{empty_seg.id}/health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["health_status"] == "INSUFFICIENT_DATA"
    assert data["health_score"] is None


@pytest.mark.asyncio
async def test_road_health_aggregation(async_client, seeded_gis_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    road_id = str(seeded_gis_context["road"].id)

    resp = await async_client.get(f"/api/v1/roads/{road_id}/health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["road_id"] == road_id
    assert data["health_score"] is not None
    assert data["health_status"] in ["GOOD", "FAIR", "POOR", "CRITICAL"]


@pytest.mark.asyncio
async def test_segment_health_history_pagination(async_client, seeded_gis_context):
    token = await get_token_for(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_gis_context["segment"].id)

    # Trigger 2 calculations to generate multiple snapshots
    await async_client.post(f"/api/v1/road-segments/{seg_id}/calculate-health", headers=headers)
    await async_client.post(f"/api/v1/road-segments/{seg_id}/calculate-health", headers=headers)

    history_resp = await async_client.get(
        f"/api/v1/road-segments/{seg_id}/health/history?page=1&page_size=10",
        headers=headers,
    )
    assert history_resp.status_code == 200
    payload = history_resp.json()
    assert len(payload["data"]) >= 2
    assert payload["meta"]["total_count"] >= 2
    assert payload["meta"]["page"] == 1


@pytest.mark.asyncio
async def test_gis_health_multi_tenant_isolation(async_client, seeded_gis_context):
    # Log in as Org 2 user
    token_org2 = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    headers_org2 = {"Authorization": f"Bearer {token_org2}", "X-Organization-ID": str(ORG_2_ID)}

    # Org 2 attempts to view Org 1 segment health
    seg_id = str(seeded_gis_context["segment"].id)
    resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/health", headers=headers_org2)
    assert resp.status_code == 404

    # Org 2 map damages should not see Org 1 damages
    map_resp = await async_client.get("/api/v1/map/damages", headers=headers_org2)
    assert map_resp.status_code == 200
    org1_dmg_ids = {str(d.id) for d in seeded_gis_context["damages"]}
    for d in map_resp.json()["data"]:
        assert d["id"] not in org1_dmg_ids


@pytest.mark.asyncio
async def test_road_health_rbac(async_client, seeded_gis_context):
    # Inspector token has road_health:read, but not road_health:calculate
    insp_token = await get_inspector_token(async_client)
    insp_headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}
    seg_id = str(seeded_gis_context["segment"].id)

    # Read is allowed
    read_resp = await async_client.get(f"/api/v1/road-segments/{seg_id}/health", headers=insp_headers)
    assert read_resp.status_code == 200

    # Calculate is forbidden for inspector without permission
    calc_resp = await async_client.post(f"/api/v1/road-segments/{seg_id}/calculate-health", headers=insp_headers)
    assert calc_resp.status_code == 403
    assert calc_resp.json()["error"]["code"] == "FORBIDDEN"
