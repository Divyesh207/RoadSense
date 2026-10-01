import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient

from app.models.damage import DamageRecord
from app.models.inspection import Inspection
from app.models.ai import DamageType
from app.models.road import Road, RoadSegment
from tests.conftest import ORG_1_ID, ORG_2_ID


async def get_token_for(async_client: AsyncClient, email: str = "authority@example.com", password: str = "AuthoritySecret123!"):
    resp = await async_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]


@pytest.fixture
def make_headers():
    def _headers(token: str, org_id: uuid.UUID = ORG_1_ID):
        return {
            "Authorization": f"Bearer {token}",
            "X-Organization-ID": str(org_id),
        }
    return _headers


@pytest.mark.asyncio
async def test_dashboard_summary(
    async_client: AsyncClient,
    make_headers,
):
    token = await get_token_for(async_client, "authority@example.com", "AuthoritySecret123!")
    headers = make_headers(token, ORG_1_ID)

    resp = await async_client.get(
        "/api/v1/dashboard/summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    summary = data["data"]
    assert "total_roads" in summary
    assert "total_segments" in summary
    assert "active_inspections" in summary
    assert "open_damages" in summary
    assert "maintenance_open" in summary
    assert "verified_repairs" in summary
    assert "recurrence_count" in summary


@pytest.mark.asyncio
async def test_damage_trends_and_filtering(
    async_client: AsyncClient,
    make_headers,
    db_session,
):
    token = await get_token_for(async_client, "authority@example.com", "AuthoritySecret123!")
    headers = make_headers(token, ORG_1_ID)

    # Seed a road and damage record
    now = datetime.now(timezone.utc)
    road = Road(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        name="Main Boulevard",
        road_code="MB-01",
        road_type="CITY_ROAD",
        is_active=True,
    )
    db_session.add(road)

    seg = RoadSegment(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        segment_number=1,
        name="MB-01-S1",
        start_chainage=0.0,
        end_chainage=5.0,
        is_active=True,
    )
    db_session.add(seg)

    dt_pothole = DamageType(id=uuid.uuid4(), code="POTHOLE_ANALYTICS", name="Pothole Test", is_active=True)
    db_session.add(dt_pothole)

    insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        road_id=road.id,
        road_segment_id=seg.id,
        inspector_user_id=uuid.uuid4(),
        status="COMPLETED",
    )
    db_session.add(insp)

    dmg = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=insp.id,
        damage_type_id=dt_pothole.id,
        road_id=road.id,
        road_segment_id=seg.id,
        confidence=0.92,
        severity="HIGH",
        status="CONFIRMED",
        created_at=now,
    )
    db_session.add(dmg)
    await db_session.commit()

    resp = await async_client.get(
        "/api/v1/analytics/damage-trends",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    trends = data["data"]
    assert "series" in trends
    assert "by_type" in trends
    assert "by_severity" in trends
    assert trends["total_damages"] >= 1
    assert "HIGH" in trends["by_severity"]


@pytest.mark.asyncio
async def test_road_health_and_maintenance_analytics(
    async_client: AsyncClient,
    make_headers,
):
    token = await get_token_for(async_client, "authority@example.com", "AuthoritySecret123!")
    headers = make_headers(token, ORG_1_ID)

    # Road health analytics
    health_resp = await async_client.get(
        "/api/v1/analytics/road-health",
        headers=headers,
    )
    assert health_resp.status_code == 200
    h_data = health_resp.json()["data"]
    assert "health_distribution" in h_data
    assert "critical_segments" in h_data

    # Maintenance analytics
    maint_resp = await async_client.get(
        "/api/v1/analytics/maintenance",
        headers=headers,
    )
    assert maint_resp.status_code == 200
    m_data = maint_resp.json()["data"]
    assert "open_jobs" in m_data
    assert "verification_rate" in m_data
    assert "recurrence_after_repair_count" in m_data

    # Inspection analytics
    insp_resp = await async_client.get(
        "/api/v1/analytics/inspections",
        headers=headers,
    )
    assert insp_resp.status_code == 200
    i_data = insp_resp.json()["data"]
    assert "total_inspections" in i_data
    assert "by_status" in i_data


@pytest.mark.asyncio
async def test_reports_lifecycle_and_download(
    async_client: AsyncClient,
    make_headers,
):
    token = await get_token_for(async_client, "authority@example.com", "AuthoritySecret123!")
    headers = make_headers(token, ORG_1_ID)

    other_token = await get_token_for(async_client, "other@example.com", "OtherSecret123!")
    other_headers = make_headers(other_token, ORG_2_ID)

    # 1. Request report generation
    payload = {
        "report_type": "ROAD_HEALTH",
        "parameters": {
            "format": "PDF",
            "timeframe": "last_30_days",
        },
    }
    create_resp = await async_client.post(
        "/api/v1/reports",
        json=payload,
        headers=headers,
    )
    assert create_resp.status_code == 202
    res_data = create_resp.json()["data"]
    report_id = res_data["report_id"]
    assert report_id is not None
    assert res_data["status"] == "COMPLETED"

    # 2. List reports
    list_resp = await async_client.get(
        "/api/v1/reports",
        headers=headers,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["meta"]["total_count"] >= 1
    assert any(r["id"] == report_id for r in list_data["data"])

    # 3. Get report detail
    detail_resp = await async_client.get(
        f"/api/v1/reports/{report_id}",
        headers=headers,
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["id"] == report_id
    assert detail["report_type"] == "ROAD_HEALTH"

    # 4. Get download URL
    dl_resp = await async_client.get(
        f"/api/v1/reports/{report_id}/download-url",
        headers=headers,
    )
    assert dl_resp.status_code == 200
    dl_data = dl_resp.json()["data"]
    assert dl_data["report_id"] == report_id
    assert "download_url" in dl_data

    # 5. Tenant isolation: Other organization user should receive 404
    other_resp = await async_client.get(
        f"/api/v1/reports/{report_id}",
        headers=other_headers,
    )
    assert other_resp.status_code == 404
