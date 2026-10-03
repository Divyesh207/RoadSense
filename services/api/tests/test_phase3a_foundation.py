"""Phase 3A: GPS damage grouping, automatic health, traffic input, historical-wear priority."""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.models.ai import AIDetection, DamageType
from app.models.damage import DamageObservation, DamageRecord
from app.models.history import RecurrenceRecord
from app.models.inspection import Inspection, InspectionMedia
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceJob
from app.models.road import Road, RoadSegment
from app.services.health_engine import calculate_segment_health
from app.services.prediction_engine import predict_segment_deterioration
from app.services.priority_engine import compute_priority
from app.services.road_lifecycle import refresh_after_damage_change
from app.services.spatial import geojson_to_wkt, point_to_wkt
from tests.conftest import INSPECTOR_USER_ID, ORG_1_ID

LAT, LON = 18.5400, 73.8500
# ~1.055 m per 1e-5 degree of longitude at this latitude.
LON_3M = 0.000028
LON_50M = 0.00047


def now():
    return datetime.now(timezone.utc)


async def auth_headers(async_client):
    resp = await async_client.post(
        "/api/v1/auth/login", json={"email": "authority@example.com", "password": "AuthoritySecret123!"}
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['data']['access_token']}", "X-Organization-ID": str(ORG_1_ID)}


@pytest_asyncio.fixture
async def ctx(db_session):
    types = {t.code: t.id for t in (await db_session.execute(select(DamageType))).scalars().all()}
    road = Road(id=uuid.uuid4(), organization_id=ORG_1_ID, name="Grouping Road", road_code="GRP-1",
                is_active=True, created_at=now())
    seg = RoadSegment(
        id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=road.id, segment_number=1, name="GRP seg 1",
        start_chainage=0.0, end_chainage=0.5, length_meters=500.0,
        geometry=geojson_to_wkt({"type": "LineString", "coordinates": [[73.8490, LAT], [73.8540, LAT]]}),
        is_active=True, created_at=now(),
    )
    insp = Inspection(
        id=uuid.uuid4(), organization_id=ORG_1_ID, inspector_user_id=INSPECTOR_USER_ID, road_id=road.id,
        road_segment_id=seg.id, status="ANALYZED", source="API", location=point_to_wkt(LAT, LON),
        gps_accuracy_meters=4.0, captured_at=now(), created_at=now(),
    )
    db_session.add_all([road, seg, insp])
    await db_session.commit()
    return {"types": types, "road": road, "segment": seg, "inspection": insp}


async def add_media(db_session, insp):
    media = InspectionMedia(
        id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=insp.id, media_type="IMAGE",
        storage_bucket="inspection-media", storage_path=f"org/insp/{uuid.uuid4()}.jpg",
        original_filename="road.jpg", mime_type="image/jpeg", file_size_bytes=1024,
        upload_status="COMPLETED", created_at=now(),
    )
    db_session.add(media)
    await db_session.commit()
    return media


async def add_detection(db_session, insp, media, type_id, lat=LAT, lon=LON, severity="HIGH"):
    det = AIDetection(
        id=uuid.uuid4(), organization_id=ORG_1_ID, ai_processing_run_id=uuid.uuid4(), inspection_id=insp.id,
        media_id=media.id, damage_type_id=type_id, confidence=0.9, bbox_x_min=0.1, bbox_y_min=0.1,
        bbox_x_max=0.4, bbox_y_max=0.4, location=point_to_wkt(lat, lon),
        raw_output={"severity_assessment": {"severity": severity, "score": 0.7}}, created_at=now(),
    )
    db_session.add(det)
    await db_session.commit()
    return det


async def promote(async_client, headers, det):
    resp = await async_client.post(f"/api/v1/damages/from-detection/{det.id}", headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# --- GPS grouping -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repeat_detection_within_gps_drift_groups_into_one_record(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    pothole = ctx["types"]["POTHOLE"]
    det1 = await add_detection(db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole)
    det2 = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole, lon=LON + LON_3M
    )

    first = await promote(async_client, headers, det1)
    second = await promote(async_client, headers, det2)

    assert second["id"] == first["id"]
    assert second["observation_count"] == 2
    resp = await async_client.get(f"/api/v1/damages/{first['id']}/observations", headers=headers)
    assert resp.status_code == 200
    obs = resp.json()["data"]
    assert [o["match_method"] for o in obs] == ["NEW_RECORD", "GPS_GROUPED"]
    assert {o["detection_id"] for o in obs} == {str(det1.id), str(det2.id)}
    assert 2.0 < obs[1]["distance_meters"] < 4.0
    assert all(o["inspection_id"] == str(ctx["inspection"].id) for o in obs)
    assert await db_session.scalar(select(func.count(DamageRecord.id))) == 1


@pytest.mark.asyncio
async def test_far_apart_detections_create_separate_records(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    pothole = ctx["types"]["POTHOLE"]
    det1 = await add_detection(db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole)
    det2 = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole, lon=LON + LON_50M
    )
    assert (await promote(async_client, headers, det1))["id"] != (await promote(async_client, headers, det2))["id"]


@pytest.mark.asyncio
async def test_different_damage_types_are_not_grouped(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    det1 = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), ctx["types"]["POTHOLE"]
    )
    det2 = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), ctx["types"]["CRACK"]
    )
    assert (await promote(async_client, headers, det1))["id"] != (await promote(async_client, headers, det2))["id"]


@pytest.mark.asyncio
async def test_detection_cannot_be_promoted_twice(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    det = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), ctx["types"]["POTHOLE"]
    )
    first = await promote(async_client, headers, det)
    again = await promote(async_client, headers, det)
    assert again["id"] == first["id"]
    assert again["observation_count"] == 1
    assert await db_session.scalar(select(func.count(DamageObservation.id))) == 1


@pytest.mark.asyncio
async def test_two_detections_in_same_photo_stay_separate(async_client, db_session, ctx):
    """Detections in one photo share its GPS point but are distinct defects."""
    headers = await auth_headers(async_client)
    media = await add_media(db_session, ctx["inspection"])
    det1 = await add_detection(db_session, ctx["inspection"], media, ctx["types"]["POTHOLE"])
    det2 = await add_detection(db_session, ctx["inspection"], media, ctx["types"]["POTHOLE"])
    assert (await promote(async_client, headers, det1))["id"] != (await promote(async_client, headers, det2))["id"]


@pytest.mark.asyncio
async def test_rejected_record_is_not_a_grouping_target(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    pothole = ctx["types"]["POTHOLE"]
    det1 = await add_detection(db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole)
    first = await promote(async_client, headers, det1)
    resp = await async_client.post(
        f"/api/v1/damages/{first['id']}/review", json={"decision": "REJECTED"}, headers=headers
    )
    assert resp.status_code == 200, resp.text
    det2 = await add_detection(db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), pothole)
    assert (await promote(async_client, headers, det2))["id"] != first["id"]


# --- Automatic health -----------------------------------------------------------------------


async def segment_snapshots(db_session, segment_id):
    return list(
        (
            await db_session.execute(
                select(RoadHealthSnapshot)
                .where(RoadHealthSnapshot.road_segment_id == segment_id)
                .order_by(RoadHealthSnapshot.calculated_at)
            )
        ).scalars().all()
    )


@pytest.mark.asyncio
async def test_health_recalculated_and_persisted_after_review(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    det = await add_detection(
        db_session, ctx["inspection"], await add_media(db_session, ctx["inspection"]), ctx["types"]["POTHOLE"]
    )
    dmg = await promote(async_client, headers, det)
    resp = await async_client.post(
        f"/api/v1/damages/{dmg['id']}/review", json={"decision": "CONFIRMED", "severity": "HIGH"}, headers=headers
    )
    assert resp.status_code == 200, resp.text

    snaps = await segment_snapshots(db_session, ctx["segment"].id)
    latest = snaps[-1]
    assert float(latest.health_score) == 85.0  # one HIGH damage: 15-point deduction
    assert latest.calculation_version == "health-v1.1.0"
    assert latest.factors["traffic"] == {
        "traffic_volume_class": None, "traffic_known": False, "traffic_multiplier": 1.0
    }

    # No duplicate snapshot when nothing changed.
    record = await db_session.get(DamageRecord, uuid.UUID(dmg["id"]))
    await refresh_after_damage_change(db_session, ORG_1_ID, [record])
    await refresh_after_damage_change(db_session, ORG_1_ID, [record])
    assert len(await segment_snapshots(db_session, ctx["segment"].id)) == len(snaps)

    road_health = await async_client.get(f"/api/v1/roads/{ctx['road'].id}/health", headers=headers)
    assert road_health.status_code == 200


async def add_damage(db_session, ctx, severity="HIGH", status="CONFIRMED", observation_count=1):
    dmg = DamageRecord(
        id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id, road_id=ctx["road"].id,
        road_segment_id=ctx["segment"].id, damage_type_id=ctx["types"]["POTHOLE"], source_type="MANUAL",
        severity=severity, status=status, location=point_to_wkt(LAT, LON), detected_at=now(),
        observation_count=observation_count, created_at=now(),
    )
    db_session.add(dmg)
    await db_session.commit()
    return dmg


async def add_recurrence(db_session, ctx, old, new, status="POTENTIAL"):
    db_session.add(RecurrenceRecord(
        id=uuid.uuid4(), organization_id=ORG_1_ID, historical_damage_id=old.id, new_damage_id=new.id,
        road_segment_id=ctx["segment"].id, status=status, evaluated_at=now(), created_at=now(), updated_at=now(),
    ))
    await db_session.commit()


@pytest.mark.asyncio
async def test_health_counts_active_recurrence_but_not_dismissed(db_session, ctx):
    old = await add_damage(db_session, ctx, status="REPAIRED")
    new = await add_damage(db_session, ctx, severity="LOW")
    await add_recurrence(db_session, ctx, old, new, "POTENTIAL")
    await add_recurrence(db_session, ctx, old, new, "DISMISSED")

    snap = await calculate_segment_health(db_session, ORG_1_ID, ctx["segment"], persist=False)
    assert snap.factors["recurrence_count"] == 1
    assert snap.factors["score_deductions"]["recurrence"] == 5.0
    assert float(snap.health_score) == 92.5  # 100 - 2.5 (LOW) - 5 (recurrence)
    assert 0.0 <= float(snap.health_score) <= 100.0


@pytest.mark.asyncio
async def test_health_score_bounded_with_heavy_damage(db_session, ctx):
    for _ in range(6):
        await add_damage(db_session, ctx, severity="CRITICAL")
    for _ in range(6):
        await add_damage(db_session, ctx, severity="HIGH")
    snap = await calculate_segment_health(db_session, ORG_1_ID, ctx["segment"], persist=False)
    assert float(snap.health_score) == 0.0
    assert snap.health_status == "CRITICAL"


# --- Road traffic input ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_road_traffic_defaults_to_unknown_and_validates(async_client):
    headers = await auth_headers(async_client)
    resp = await async_client.post("/api/v1/roads", json={"name": "No Traffic Data Rd"}, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()["data"]
    assert data["traffic_volume_class"] is None and data["traffic_aadt"] is None
    assert data["traffic_data_source"] is None

    bad = await async_client.post(
        "/api/v1/roads", json={"name": "Bad", "traffic_volume_class": "EXTREME"}, headers=headers
    )
    assert bad.status_code == 422
    bad = await async_client.post("/api/v1/roads", json={"name": "Bad", "traffic_aadt": -5}, headers=headers)
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_traffic_class_scales_health_and_can_be_cleared(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    await add_damage(db_session, ctx, severity="HIGH")
    road_id = ctx["road"].id

    resp = await async_client.patch(
        f"/api/v1/roads/{road_id}",
        json={"traffic_volume_class": "HIGH", "traffic_aadt": 18000, "traffic_data_source": "PWD count 2025"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["traffic_volume_class"] == "HIGH"
    latest = (await segment_snapshots(db_session, ctx["segment"].id))[-1]
    assert float(latest.health_score) == 82.0  # 15 * 1.2
    assert latest.factors["traffic"]["traffic_known"] is True

    resp = await async_client.patch(
        f"/api/v1/roads/{road_id}",
        json={"traffic_volume_class": None, "traffic_aadt": None, "traffic_data_source": None},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["traffic_volume_class"] is None
    latest = (await segment_snapshots(db_session, ctx["segment"].id))[-1]
    assert float(latest.health_score) == 85.0
    assert latest.factors["traffic"]["traffic_known"] is False


# --- Priority -------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_priority_adds_historical_wear_components(db_session, ctx):
    dmg = await add_damage(db_session, ctx, severity="HIGH", observation_count=3)
    base = await compute_priority(db_session, ORG_1_ID, [dmg], ctx["road"].id, ctx["segment"].id)
    assert base.factors["components"]["severity_base"] == 68.0
    assert base.factors["components"]["frequency"] == 4  # 2 repeat observations
    assert base.factors["inputs"]["road_health_score"] is None
    assert base.score == 72.0

    old = await add_damage(db_session, ctx, status="REPAIRED")
    await add_recurrence(db_session, ctx, old, dmg)
    db_session.add(MaintenanceJob(
        id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=ctx["road"].id, road_segment_id=ctx["segment"].id,
        created_by_user_id=INSPECTOR_USER_ID, title="Earlier repair", priority_level="HIGH", status="VERIFIED", created_at=now(), updated_at=now(),
    ))
    await db_session.commit()
    await calculate_segment_health(db_session, ORG_1_ID, ctx["segment"], persist=True)

    worn = await compute_priority(db_session, ORG_1_ID, [dmg], ctx["road"].id, ctx["segment"].id)
    comps = worn.factors["components"]
    assert comps["recurrence"] == 5
    assert comps["prior_repairs"] == 4
    # health 80 (HIGH -15, recurrence -5) -> 0.15 * 20 = 3
    assert comps["road_health"] == 3.0
    assert worn.score == 68.0 + 4 + 5 + 4 + 3.0
    assert worn.level in ("HIGH", "CRITICAL")

    again = await compute_priority(db_session, ORG_1_ID, [dmg], ctx["road"].id, ctx["segment"].id)
    assert (again.level, again.score, again.factors["components"]) == (worn.level, worn.score, comps)


@pytest.mark.asyncio
async def test_auto_priority_updates_but_manual_priority_is_kept(async_client, db_session, ctx):
    headers = await auth_headers(async_client)
    d_auto = await add_damage(db_session, ctx, severity="HIGH")
    d_manual = await add_damage(db_session, ctx, severity="HIGH")
    base = {"road_id": str(ctx["road"].id), "road_segment_id": str(ctx["segment"].id)}
    auto = await async_client.post(
        "/api/v1/maintenance-jobs", headers=headers,
        json={**base, "title": "Auto", "damage_record_ids": [str(d_auto.id)]},
    )
    manual = await async_client.post(
        "/api/v1/maintenance-jobs", headers=headers,
        json={**base, "title": "Manual", "priority": "LOW", "priority_score": 10, "damage_record_ids": [str(d_manual.id)]},
    )
    assert auto.status_code == 201 and manual.status_code == 201, (auto.text, manual.text)
    auto_data, manual_data = auto.json()["data"], manual.json()["data"]
    assert auto_data["priority_factors"]["mode"] == "AUTO"
    assert manual_data["priority_factors"]["mode"] == "MANUAL"
    assert manual_data["priority_level"] == "LOW" and manual_data["priority_score"] == 10

    old = await add_damage(db_session, ctx, status="REPAIRED")
    await add_recurrence(db_session, ctx, old, d_auto)
    await refresh_after_damage_change(db_session, ORG_1_ID, [d_auto, d_manual])

    auto_job = await db_session.get(MaintenanceJob, uuid.UUID(auto_data["id"]))
    manual_job = await db_session.get(MaintenanceJob, uuid.UUID(manual_data["id"]))
    await db_session.refresh(auto_job)
    await db_session.refresh(manual_job)
    assert float(auto_job.priority_score) > auto_data["priority_score"]
    assert auto_job.priority_factors["components"]["recurrence"] == 5
    assert manual_job.priority_level == "LOW" and float(manual_job.priority_score) == 10.0


# --- Prediction -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prediction_uses_analyzed_inspections(db_session, ctx):
    await add_damage(db_session, ctx, severity="HIGH")
    await calculate_segment_health(db_session, ORG_1_ID, ctx["segment"], persist=True)
    prediction = await predict_segment_deterioration(db_session, ORG_1_ID, ctx["segment"], persist=False)
    assert prediction.status != "INSUFFICIENT_DATA"
    assert prediction.features.get("has_inspection", True) is True
