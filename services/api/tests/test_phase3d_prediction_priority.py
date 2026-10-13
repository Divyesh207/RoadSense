"""Phase 3D: honest rule-based deterioration estimate (feature pipeline v2, trend-only
projection, training-readiness report) and priority with escalation/estimate components."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.inspection import Inspection
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceJob
from app.models.road import Road, RoadSegment
from app.services.prediction_engine import health_trend, rule_based_estimate
from app.services.spatial import point_to_wkt
from tests.conftest import INSPECTOR_USER_ID, ORG_1_ID


def now():
    return datetime.now(UTC)


async def headers(async_client):
    r = await async_client.post("/api/v1/auth/login", json={"email": "authority@example.com", "password": "AuthoritySecret123!"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}", "X-Organization-ID": str(ORG_1_ID)}


def features(**over):
    base = {
        "critical_damage_count": 0, "high_damage_count": 1, "medium_damage_count": 0, "low_damage_count": 0,
        "current_health_score": 80.0, "health_trend_points_per_day": None, "recurrence_count": 0,
        "escalated_recurrence_count": 0, "last_repair_verification_result": None,
        "days_since_last_inspection": 0, "traffic_volume_class": None,
    }
    return {**base, **over}


# --- estimate rules -------------------------------------------------------------------------


def test_trend_requires_two_snapshots_spanning_a_week():
    t = now()
    assert health_trend([]) == (None, 0, 0)
    assert health_trend([(t, 90.0)])[0] is None
    assert health_trend([(t, 90.0), (t + timedelta(days=3), 80.0)])[0] is None
    slope, n, span = health_trend([(t, 90.0), (t + timedelta(days=10), 80.0), (t + timedelta(days=20), 70.0)])
    assert slope == pytest.approx(-1.0) and n == 3 and span == 20


def test_no_projection_or_trend_points_without_observed_trend():
    est = rule_based_estimate(features(), 90)
    assert est["projected_health"] is None and est["projection_method"] is None
    assert est["contributions"]["health_trend"] == 0.0
    assert any("No observed health trend" in n for n in est["notes"])
    assert any("Traffic volume unknown" in n for n in est["notes"])
    parts = {k: v for k, v in est["contributions"].items() if k != "horizon_factor"}
    assert est["risk"] == pytest.approx(round(sum(parts.values()) * est["contributions"]["horizon_factor"], 2))


def test_trend_projection_and_history_factors():
    est = rule_based_estimate(
        features(health_trend_points_per_day=-0.1, recurrence_count=2, escalated_recurrence_count=1,
                 last_repair_verification_result="SUBSTANDARD", traffic_volume_class="HIGH"),
        90,
    )
    assert est["projected_health"] == pytest.approx(71.0)  # 80 - 0.1 * 90
    assert est["projection_method"] == "LINEAR_TREND_EXTRAPOLATION"
    c = est["contributions"]
    assert c["health_trend"] == pytest.approx(4.5)
    assert c["recurrence"] == 16.0 and c["repair_quality"] == 8.0 and c["traffic"] == 3.0
    assert est["risk_band"] in ("LOW", "MODERATE", "HIGH", "SEVERE")
    # Rising health never adds trend risk.
    assert rule_based_estimate(features(health_trend_points_per_day=0.2), 90)["contributions"]["health_trend"] == 0.0


# --- API: estimate + priority ---------------------------------------------------------------


@pytest_asyncio.fixture
async def ctx(db_session):
    types = {t.code: t.id for t in (await db_session.execute(select(DamageType))).scalars().all()}
    road = Road(id=uuid.uuid4(), organization_id=ORG_1_ID, name="Trend Rd", is_active=True, created_at=now())
    seg = RoadSegment(id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=road.id, segment_number=1, length_meters=500.0,
                      is_active=True, created_at=now())
    insp = Inspection(id=uuid.uuid4(), organization_id=ORG_1_ID, inspector_user_id=INSPECTOR_USER_ID, road_id=road.id,
                      road_segment_id=seg.id, status="ANALYZED", source="API", location=point_to_wkt(18.6, 73.9),
                      captured_at=now(), created_at=now())
    dmg = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=insp.id, road_id=road.id,
                       road_segment_id=seg.id, damage_type_id=types["POTHOLE"], source_type="MANUAL", severity="HIGH",
                       status="CONFIRMED", location=point_to_wkt(18.6, 73.9), created_at=now())
    db_session.add_all([road, seg, insp, dmg])
    for days_ago, score in ((20, 90.0), (0, 70.0)):
        db_session.add(RoadHealthSnapshot(
            id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=road.id, road_segment_id=seg.id, health_score=score,
            health_status="FAIR", calculation_version="health-v1.1.0", factors={},
            calculated_at=now() - timedelta(days=days_ago), created_at=now(),
        ))
    await db_session.commit()
    return {"road": road, "segment": seg, "damage": dmg}


@pytest.mark.asyncio
async def test_estimate_uses_observed_trend_and_reports_training_readiness(async_client, ctx):
    h = await headers(async_client)
    resp = await async_client.post(f"/api/v1/road-segments/{ctx['segment'].id}/predictions", headers=h,
                                   json={"prediction_horizon_days": 30})
    assert resp.status_code == 200, resp.text
    d = resp.json()["data"]
    f = d["features"]
    assert d["estimation_method"] == "RULE_BASED_ESTIMATE" and d["model_version"] == "rules-v2"
    assert d["confidence"] is None and d["uncertainty_lower"] is None
    assert f["health_trend_points_per_day"] == pytest.approx(-1.0, abs=0.01)
    assert f["projection_method"] == "LINEAR_TREND_EXTRAPOLATION"
    assert d["predicted_value"] == pytest.approx(40.0, abs=0.5)  # 70 - 1.0/day * 30 days
    assert f["contributions"]["health_trend"] == 15.0  # capped
    assert f["ml_training_readiness"] == {
        "segments_with_outcome_history": 0, "required_segments": 30, "required_span_days": 30,
        "status": "INSUFFICIENT_DATA", "model_trained": False,
    }


@pytest.mark.asyncio
async def test_priority_includes_escalation_and_estimate_and_dashboard_ranks(async_client, db_session, ctx):
    h = await headers(async_client)
    job = (await async_client.post("/api/v1/maintenance-jobs", headers=h, json={
        "title": "Trend road repair", "road_id": str(ctx["road"].id), "road_segment_id": str(ctx["segment"].id),
        "damage_record_ids": [str(ctx["damage"].id)]})).json()["data"]
    assert job["priority_factors"]["version"] == "priority-v2.1.0"
    assert job["priority_factors"]["components"]["escalation"] == 0.0
    assert job["priority_factors"]["components"]["deterioration_estimate"] == 0.0

    old = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["damage"].inspection_id,
                       road_id=ctx["road"].id, road_segment_id=ctx["segment"].id,
                       damage_type_id=ctx["damage"].damage_type_id, source_type="MANUAL", severity="HIGH",
                       status="REPAIRED", created_at=now() - timedelta(days=60))
    db_session.add(old)
    await db_session.flush()
    db_session.add(RecurrenceRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, historical_damage_id=old.id,
                                    new_damage_id=ctx["damage"].id, road_segment_id=ctx["segment"].id,
                                    status="POTENTIAL", escalation_level="CRITICAL", escalation_reasons=[],
                                    evaluated_at=now(), created_at=now(), updated_at=now()))
    await db_session.commit()

    pred = (await async_client.post(f"/api/v1/road-segments/{ctx['segment'].id}/predictions", headers=h,
                                    json={"prediction_horizon_days": 90})).json()["data"]
    j = await db_session.get(MaintenanceJob, uuid.UUID(job["id"]))
    await db_session.refresh(j)
    comps, inputs = j.priority_factors["components"], j.priority_factors["inputs"]
    assert comps["escalation"] == 10.0 and inputs["recurrence_escalation_level"] == "CRITICAL"
    assert comps["deterioration_estimate"] == pytest.approx(min(10.0, pred["predicted_risk"] * 0.1), abs=0.01)
    assert inputs["deterioration_estimate_method"] == "RULE_BASED_ESTIMATE"
    assert inputs["traffic_volume_class"] is None

    db_session.add(MaintenanceJob(id=uuid.uuid4(), organization_id=ORG_1_ID, created_by_user_id=INSPECTOR_USER_ID,
                                  title="Minor", priority_level="LOW", priority_score=10, status="OPEN",
                                  created_at=now(), updated_at=now()))
    await db_session.commit()
    rows = (await async_client.get("/api/v1/analytics/priorities", headers=h)).json()["data"]
    assert [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
    top = rows[0]
    assert top["job_id"] == job["id"] and top["escalation_level"] == "CRITICAL"
    assert top["components"]["escalation"] == 10.0
    assert top["deterioration_estimate"]["method"] == "RULE_BASED_ESTIMATE"
    assert rows[-1]["title"] == "Minor" and rows[-1]["components"] is None
