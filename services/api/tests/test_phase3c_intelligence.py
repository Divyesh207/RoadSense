"""Phase 3C: automatic rule-based recurrence + escalation, contractor history, dashboard
summary from real states, road intelligence timeline and map context."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.ai import DamageType
from app.models.damage import DamageRecord
from app.models.history import AuditLog, RecurrenceRecord
from app.models.inspection import Inspection
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.repair import RepairVerification
from app.models.road import Road, RoadSegment
from app.services.spatial import geojson_to_wkt, point_to_wkt
from tests.conftest import AUTHORITY_USER_ID, CREW_USER_ID, INSPECTOR_USER_ID, ORG_1_ID

LAT, LON = 18.5600, 73.8000
LON_3M = 0.000028


def now():
    return datetime.now(timezone.utc)


async def headers(async_client):
    r = await async_client.post("/api/v1/auth/login", json={"email": "authority@example.com", "password": "AuthoritySecret123!"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}", "X-Organization-ID": str(ORG_1_ID)}


@pytest_asyncio.fixture
async def ctx(db_session):
    types = {t.code: t.id for t in (await db_session.execute(select(DamageType))).scalars().all()}
    road = Road(id=uuid.uuid4(), organization_id=ORG_1_ID, name="Recurrence Rd", road_code="REC-1", is_active=True,
                created_at=now())
    seg = RoadSegment(
        id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=road.id, segment_number=1, name="REC seg",
        length_meters=400.0, is_active=True, created_at=now(),
        geometry=geojson_to_wkt({"type": "LineString", "coordinates": [[73.7990, LAT], [73.8030, LAT]]}),
    )
    insp = Inspection(id=uuid.uuid4(), organization_id=ORG_1_ID, inspector_user_id=INSPECTOR_USER_ID, road_id=road.id,
                      road_segment_id=seg.id, status="ANALYZED", source="API", location=point_to_wkt(LAT, LON),
                      captured_at=now(), created_at=now())
    db_session.add_all([road, seg, insp])
    await db_session.commit()
    return {"types": types, "road": road, "segment": seg, "inspection": insp}


async def repaired_damage(db_session, ctx, days_ago=200, result="SUCCESSFUL", severity="HIGH", type_code="POTHOLE",
                          assignee=CREW_USER_ID):
    """Historical damage repaired by a job; `result` is the reviewer's final verification outcome."""
    t = now() - timedelta(days=days_ago)
    dmg = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id,
                       road_id=ctx["road"].id, road_segment_id=ctx["segment"].id, damage_type_id=ctx["types"][type_code],
                       source_type="MANUAL", severity=severity, status="REPAIRED", location=point_to_wkt(LAT, LON),
                       detected_at=t - timedelta(days=20), created_at=t - timedelta(days=20), updated_at=t)
    job = MaintenanceJob(id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=ctx["road"].id,
                         road_segment_id=ctx["segment"].id, created_by_user_id=AUTHORITY_USER_ID,
                         assigned_to_user_id=assignee, title="Earlier patch", priority_level="HIGH",
                         status="VERIFIED" if result == "SUCCESSFUL" else "REJECTED", completed_at=t,
                         verified_at=t if result == "SUCCESSFUL" else None, created_at=t - timedelta(days=10), updated_at=t)
    db_session.add_all([dmg, job])
    await db_session.flush()
    db_session.add(MaintenanceDamageLink(maintenance_job_id=job.id, damage_record_id=dmg.id, relationship_type="PRIMARY",
                                         created_at=t))
    if result is not None:
        db_session.add(RepairVerification(
            id=uuid.uuid4(), organization_id=ORG_1_ID, maintenance_job_id=job.id, verification_type="HUMAN_REVIEW",
            verification_status="REVIEWED", result=result, review_decision="CONFIRMED", previous_result=result,
            verified_by_user_id=AUTHORITY_USER_ID, verified_at=t, findings={}, created_at=t, updated_at=t,
        ))
    await db_session.commit()
    return dmg, job


async def create_confirmed(async_client, h, ctx, severity="MEDIUM", lon=LON + LON_3M, type_code="POTHOLE"):
    resp = await async_client.post("/api/v1/damages", headers=h, json={
        "inspection_id": str(ctx["inspection"].id), "damage_type_id": str(ctx["types"][type_code]),
        "severity": severity, "location": {"latitude": LAT, "longitude": lon},
        "road_id": str(ctx["road"].id), "road_segment_id": str(ctx["segment"].id),
    })
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


async def recurrences(db_session):
    stmt = select(RecurrenceRecord).execution_options(populate_existing=True)
    return (await db_session.execute(stmt)).scalars().all()


# --- automatic recurrence -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_confirmed_damage_near_repaired_location_creates_recurrence(async_client, db_session, ctx):
    h = await headers(async_client)
    hist, job = await repaired_damage(db_session, ctx)
    new = await create_confirmed(async_client, h, ctx, severity="MEDIUM")
    recs = await recurrences(db_session)
    assert len(recs) == 1
    r = recs[0]
    assert (str(r.historical_damage_id), str(r.new_damage_id)) == (str(hist.id), new["id"])
    assert r.related_maintenance_job_id == job.id and r.status == "POTENTIAL"
    f = r.rule_factors
    assert f["rules_version"] == "recurrence-rules-v1.0.0"
    assert 2.0 < f["distance_meters"] < 4.0 and f["same_damage_type"] is True
    assert f["previous_verification_result"] == "SUCCESSFUL" and f["days_since_repair"] >= 199
    assert r.escalation_level == "NONE" and r.escalation_reasons == []
    # Original repair history untouched.
    await db_session.refresh(hist)
    assert hist.status == "REPAIRED"
    # Health now counts the recurrence.
    snap = (await db_session.execute(
        select(RoadHealthSnapshot).where(RoadHealthSnapshot.road_segment_id == ctx["segment"].id)
        .order_by(RoadHealthSnapshot.calculated_at.desc())
    )).scalars().first()
    assert snap.factors["recurrence_count"] == 1
    assert snap.factors["score_deductions"]["recurrence"] == 5.0


@pytest.mark.asyncio
async def test_no_recurrence_without_repair_other_type_or_outside_radius(async_client, db_session, ctx):
    h = await headers(async_client)
    open_dmg = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id,
                            road_id=ctx["road"].id, road_segment_id=ctx["segment"].id,
                            damage_type_id=ctx["types"]["POTHOLE"], source_type="MANUAL", severity="HIGH",
                            status="CONFIRMED", location=point_to_wkt(LAT, LON), created_at=now() - timedelta(days=5))
    db_session.add(open_dmg)
    await db_session.commit()
    await create_confirmed(async_client, h, ctx)  # near open (never repaired) damage
    await repaired_damage(db_session, ctx, type_code="CRACK")
    await create_confirmed(async_client, h, ctx, type_code="POTHOLE")  # repaired damage is another type
    await create_confirmed(async_client, h, ctx, type_code="CRACK", lon=LON + 0.0005)  # ~53 m away
    assert await recurrences(db_session) == []


@pytest.mark.asyncio
async def test_escalation_rules_and_audit(async_client, db_session, ctx):
    h = await headers(async_client)
    await repaired_damage(db_session, ctx, days_ago=10, result="SUBSTANDARD")
    await create_confirmed(async_client, h, ctx, severity="HIGH")
    r = (await recurrences(db_session))[0]
    codes = {x["code"] for x in r.escalation_reasons}
    assert codes == {"SUBSTANDARD_REPAIR", "EARLY_RECURRENCE", "HIGH_SEVERITY"}
    assert r.escalation_level == "ELEVATED" and r.escalated_at is not None
    audit = (await db_session.execute(select(AuditLog).where(AuditLog.action == "RECURRENCE_ESCALATED"))).scalars().all()
    assert len(audit) == 1 and audit[0].after_data["escalation_level"] == "ELEVATED"


@pytest.mark.asyncio
async def test_repeated_recurrence_escalates_to_critical(db_session, ctx):
    from app.services.recurrence_engine import evaluate_recurrence

    hist, _ = await repaired_damage(db_session, ctx)
    prev = hist
    levels = []
    for i in range(3):
        new = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id,
                           road_id=ctx["road"].id, road_segment_id=ctx["segment"].id,
                           damage_type_id=ctx["types"]["POTHOLE"], source_type="MANUAL", severity="LOW",
                           status="CONFIRMED", location=point_to_wkt(LAT, LON + LON_3M),
                           detected_at=now() + timedelta(seconds=i), created_at=now() + timedelta(seconds=i))
        db_session.add(new)
        await db_session.flush()
        created = await evaluate_recurrence(db_session, ORG_1_ID, new, actor_user_id=AUTHORITY_USER_ID)
        await db_session.commit()
        rec = next(c for c in created if c.historical_damage_id == prev.id)
        levels.append((rec.rule_factors["recurrence_number_at_location"], rec.escalation_level))
        # Model the chain: this damage gets repaired, then recurs again.
        new.status = "REPAIRED"
        await db_session.commit()
        prev = new
    assert levels[0] == (1, "NONE")
    assert levels[1][0] == 2 and levels[1][1] in ("ELEVATED", "CRITICAL")
    assert levels[2][0] >= 3 and levels[2][1] == "CRITICAL"


@pytest.mark.asyncio
async def test_pending_ai_damage_only_recurs_once_confirmed_and_rejection_dismisses(async_client, db_session, ctx):
    h = await headers(async_client)
    await repaired_damage(db_session, ctx)
    pending = DamageRecord(id=uuid.uuid4(), organization_id=ORG_1_ID, inspection_id=ctx["inspection"].id,
                           road_id=ctx["road"].id, road_segment_id=ctx["segment"].id,
                           damage_type_id=ctx["types"]["POTHOLE"], source_type="AI", severity="MEDIUM",
                           status="PENDING_REVIEW", location=point_to_wkt(LAT, LON + LON_3M), created_at=now())
    db_session.add(pending)
    await db_session.commit()
    assert await recurrences(db_session) == []
    ok = await async_client.post(f"/api/v1/damages/{pending.id}/review", headers=h, json={"decision": "CONFIRMED"})
    assert ok.status_code == 200, ok.text
    recs = await recurrences(db_session)
    assert len(recs) == 1 and recs[0].status == "POTENTIAL"
    # Reviewer later corrects the decision via PATCH -> the recurrence is dismissed, not deleted.
    rej = await async_client.patch(f"/api/v1/damages/{pending.id}", headers=h, json={"status": "REJECTED"})
    assert rej.status_code == 200, rej.text
    recs = await recurrences(db_session)
    assert len(recs) == 1 and recs[0].status == "DISMISSED"
    assert "rejected" in recs[0].review_notes


# --- read models ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contractor_history_from_real_jobs(async_client, db_session, ctx):
    h = await headers(async_client)
    await repaired_damage(db_session, ctx, result="SUCCESSFUL")
    await create_confirmed(async_client, h, ctx)
    resp = await async_client.get("/api/v1/analytics/contractors", headers=h)
    assert resp.status_code == 200, resp.text
    crew = next(x for x in resp.json()["data"] if x["assignee_id"] == str(CREW_USER_ID))
    assert crew["assignee_type"] == "USER"
    assert crew["assigned_jobs"] == 1 and crew["completed_jobs"] == 1 and crew["verified_jobs"] == 1
    assert crew["verification_outcomes"] == {"SUCCESSFUL": 1}
    assert crew["recurrences_after_repair"] == 1


@pytest.mark.asyncio
async def test_dashboard_summary_counts_real_states(async_client, db_session, ctx):
    h = await headers(async_client)
    await repaired_damage(db_session, ctx, days_ago=5, result="SUBSTANDARD")
    await create_confirmed(async_client, h, ctx, severity="CRITICAL")
    db_session.add(MaintenanceJob(id=uuid.uuid4(), organization_id=ORG_1_ID, created_by_user_id=AUTHORITY_USER_ID,
                                  title="Awaiting verification", priority_level="HIGH", status="VERIFICATION_PENDING",
                                  created_at=now(), updated_at=now()))
    await db_session.commit()
    s = (await async_client.get("/api/v1/dashboard/summary", headers=h)).json()["data"]
    assert s["maintenance_by_status"].get("VERIFICATION_PENDING") == 1
    assert s["verification_pending"] == 1
    assert s["maintenance_by_status"].get("REJECTED") == 1
    assert s["critical_damages"] == 1
    assert s["recurrence_count"] == 1 and s["escalated_recurrences"] == 1
    assert s["repair_verification_results"] == {"SUBSTANDARD": 1}
    assert s["average_road_health"] is not None and s["roads_with_health"] == 1


@pytest.mark.asyncio
async def test_insufficient_data_segment_is_not_scored(async_client, db_session, ctx):
    h = await headers(async_client)
    db_session.add(RoadHealthSnapshot(id=uuid.uuid4(), organization_id=ORG_1_ID, road_id=ctx["road"].id,
                                      road_segment_id=ctx["segment"].id, health_score=None,
                                      health_status="INSUFFICIENT_DATA", calculation_version="health-v1.1.0",
                                      factors={}, calculated_at=now(), created_at=now()))
    await db_session.commit()
    data = (await async_client.get("/api/v1/analytics/road-health", headers=h)).json()["data"]
    assert data["average_health"] is None
    assert data["total_segments_evaluated"] == 0 and data["segments_insufficient_data"] == 1


@pytest.mark.asyncio
async def test_road_intelligence_timeline_and_overviews(async_client, db_session, ctx):
    h = await headers(async_client)
    await repaired_damage(db_session, ctx, days_ago=30, result="SUCCESSFUL")
    await create_confirmed(async_client, h, ctx, severity="HIGH")
    resp = await async_client.get(f"/api/v1/roads/{ctx['road'].id}/intelligence", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    types = {e["type"] for e in data["timeline"]}
    assert {"INSPECTION", "DAMAGE", "HEALTH", "PRIORITY", "VERIFICATION", "RECURRENCE"} <= types
    assert [e["at"] for e in data["timeline"]] == sorted(e["at"] for e in data["timeline"])
    assert data["segment_health_history"][str(ctx["segment"].id)][-1]["recurrence_count"] == 1
    assert data["summary"]["active_recurrences"] == 1 and data["summary"]["repaired_damages"] == 1

    recs = (await async_client.get("/api/v1/analytics/recurrences", headers=h)).json()["data"]
    assert recs[0]["previous_verification_result"] == "SUCCESSFUL"
    assert recs[0]["previous_repair_job_title"] == "Earlier patch"
    assert recs[0]["road_name"] == "Recurrence Rd"

    feats = (await async_client.get("/api/v1/map/damages", headers=h)).json()["data"]
    new_feat = next(f for f in feats if f["status"] == "CONFIRMED")
    old_feat = next(f for f in feats if f["status"] == "REPAIRED")
    assert new_feat["active_recurrences"] == 1 and old_feat["maintenance_status"] == "VERIFIED"
    assert new_feat["segment_health_score"] is not None
    other = await async_client.get(f"/api/v1/roads/{uuid.uuid4()}/intelligence", headers=h)
    assert other.status_code == 404
