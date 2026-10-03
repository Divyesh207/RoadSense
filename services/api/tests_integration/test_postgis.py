"""Schema, PostGIS functions and spatial API behaviour on a real PostgreSQL/PostGIS."""

import math
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

EXPECTED_GIST = {
    ("roads", "geometry"),
    ("road_segments", "geometry"),
    ("inspections", "location"),
    ("inspection_media", "location"),
    ("ai_detections", "location"),
    ("damage_records", "location"),
    ("damage_observations", "location"),
    ("maintenance_jobs", "location"),
    ("repair_evidence", "location"),
}


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@pytest.mark.asyncio
async def test_migrated_schema_has_all_tables_postgis_and_one_gist_per_spatial_column(pg_engine):
    from app.models import Base

    async with pg_engine.connect() as conn:
        tables = set(
            (
                await conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' "
                        "AND table_type='BASE TABLE' AND table_name NOT IN ('alembic_version','spatial_ref_sys')"
                    )
                )
            ).scalars()
        )
        version = (await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname='postgis'"))).scalar_one()
        server = (await conn.execute(text("SHOW server_version_num"))).scalar_one()
        gist = (
            await conn.execute(
                text(
                    "SELECT t.relname, a.attname FROM pg_index i "
                    "JOIN pg_class c ON c.oid = i.indexrelid JOIN pg_class t ON t.oid = i.indrelid "
                    "JOIN pg_am am ON am.oid = c.relam JOIN pg_namespace n ON n.oid = t.relnamespace "
                    "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey) "
                    "WHERE am.amname = 'gist' AND n.nspname = 'public'"
                )
            )
        ).all()
        geom_cols = {
            (r.f_table_name, r.f_geometry_column): (r.type, r.srid)
            for r in await conn.execute(
                text("SELECT f_table_name, f_geometry_column, type, srid FROM geometry_columns WHERE f_table_schema='public'")
            )
        }
        revision = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()

    assert len(tables) == 31
    assert tables == set(Base.metadata.tables)
    assert version.startswith("3.4")
    assert int(server) // 10000 == 16
    assert revision == "004_phase3b_repair_verif"
    indexed = [(t, c) for t, c in gist]
    assert set(indexed) == EXPECTED_GIST
    assert len(indexed) == len(EXPECTED_GIST), "each spatial column must have exactly one GIST index"
    assert geom_cols[("road_segments", "geometry")] == ("LINESTRING", 4326)
    assert geom_cols[("inspections", "location")] == ("POINT", 4326)


@pytest.mark.asyncio
async def test_postgis_distance_functions_geometry_vs_geography(pg_engine):
    line = "SRID=4326;LINESTRING(73.8500 18.5200, 73.8550 18.5200)"
    near = "SRID=4326;POINT(73.8525 18.5203)"  # ~33 m north of the midpoint
    async with pg_engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT ST_Distance(CAST(:l AS geography), CAST(:p AS geography)) AS geog_m, "
                    "ST_Distance(CAST(:l AS geometry), CAST(:p AS geometry)) AS geom_deg, "
                    "ST_DWithin(CAST(:l AS geography), CAST(:p AS geography), 40) AS within_40, "
                    "ST_DWithin(CAST(:l AS geography), CAST(:p AS geography), 25) AS within_25, "
                    "ST_LineLocatePoint(CAST(:l AS geometry), CAST(:p AS geometry)) AS frac, "
                    "ST_Length(CAST(:l AS geography)) AS len_m"
                ),
                {"l": line, "p": near},
            )
        ).one()

    expected = haversine_m(18.5200, 73.8525, 18.5203, 73.8525)
    assert abs(row.geog_m - expected) < 0.5  # metres on the spheroid
    assert abs(row.geom_deg - 0.0003) < 1e-9  # planar degrees, not metres
    assert row.within_40 is True and row.within_25 is False
    assert abs(row.frac - 0.5) < 1e-6
    assert abs(row.len_m - haversine_m(18.52, 73.85, 18.52, 73.855)) < 2.0


async def _road_with_segments(client) -> tuple[str, list[str]]:
    road = await client.post(
        "/api/v1/roads",
        json={
            "name": "FC Road",
            "road_code": "FC-01",
            "road_type": "ARTERIAL",
            "geometry": {"type": "LineString", "coordinates": [[73.8500, 18.5200], [73.8600, 18.5200]]},
        },
    )
    assert road.status_code == 201, road.text
    road_id = road.json()["data"]["id"]
    seg_ids = []
    for n, coords in enumerate([[[73.8500, 18.5200], [73.8550, 18.5200]], [[73.8550, 18.5200], [73.8600, 18.5200]]], 1):
        seg = await client.post(
            f"/api/v1/roads/{road_id}/segments",
            json={"segment_number": n, "name": f"S{n}", "geometry": {"type": "LineString", "coordinates": coords}},
        )
        assert seg.status_code == 201, seg.text
        seg_ids.append(seg.json()["data"]["id"])
    return road_id, seg_ids


@pytest.mark.asyncio
async def test_match_location_uses_postgis_and_agrees_with_geodesic_distance(api_client):
    _, (seg1, _seg2) = await _road_with_segments(api_client)

    resp = await api_client.post(
        "/api/v1/roads/match-location", json={"latitude": 18.52010, "longitude": 73.85125, "max_distance_meters": 50}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    best = data["best_match"]
    assert best["segment_id"] == seg1
    assert abs(best["distance_meters"] - haversine_m(18.5200, 73.85125, 18.52010, 73.85125)) < 0.5
    assert abs(best["position_along_segment"] - 0.25) < 0.01  # only the PostGIS path computes this
    assert [c["segment_id"] for c in data["candidates"]] == [seg1]  # seg2 is ~140 m away

    far = await api_client.post(
        "/api/v1/roads/match-location", json={"latitude": 18.5300, "longitude": 73.8550, "max_distance_meters": 50}
    )
    assert far.json()["data"]["matched"] is False


@pytest.mark.asyncio
async def test_bbox_prefilter_does_not_drop_matches_at_high_latitude(api_client):
    # Longitude degrees shrink with latitude; the &&/ST_Expand prefilter must still cover the radius.
    road = await api_client.post("/api/v1/roads", json={"name": "Arctic", "road_code": "AR-1"})
    road_id = road.json()["data"]["id"]
    seg = await api_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={"segment_number": 1, "geometry": {"type": "LineString", "coordinates": [[25.0, 70.0], [25.0, 70.01]]}},
    )
    seg_id = seg.json()["data"]["id"]
    # ~95 m east of the segment at 70°N (0.0025° lon ≈ 95 m)
    resp = await api_client.post(
        "/api/v1/roads/match-location", json={"latitude": 70.005, "longitude": 25.0025, "max_distance_meters": 100}
    )
    best = resp.json()["data"]["best_match"]
    assert best is not None and best["segment_id"] == seg_id
    assert 90 < best["distance_meters"] < 100


@pytest.mark.asyncio
async def test_inspection_pipeline_persists_detections_with_postgis_geometry(api_client, session_factory, monkeypatch, tmp_path):
    """API (create/upload/submit/process) -> worker pipeline -> PostGIS rows."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    worker_dir = Path(__file__).resolve().parents[2] / "ai-worker"
    sys.path.insert(0, str(worker_dir))
    try:
        from inference.model_registry import ModelRegistry
        from pipelines.media_pipeline import execute_inspection_pipeline
    finally:
        sys.path.remove(str(worker_dir))
    monkeypatch.setenv("YOLO_MODEL_PATH", str(tmp_path / "no-weights.pt"))
    ModelRegistry.reset()

    _, (seg1, _) = await _road_with_segments(api_client)
    insp = await api_client.post(
        "/api/v1/inspections",
        json={"road_segment_id": seg1, "location": {"latitude": 18.5201, "longitude": 73.8525, "accuracy_m": 4.0}},
    )
    assert insp.status_code == 201, insp.text
    insp_id = insp.json()["data"]["id"]

    image = np.full((480, 640, 3), 130, dtype=np.uint8)
    cv2.circle(image, (320, 240), 50, (20, 20, 20), -1)
    ok, jpeg = cv2.imencode(".jpg", image)
    assert ok

    up = (
        await api_client.post(
            f"/api/v1/inspections/{insp_id}/media/upload-url",
            json={"filename": "road.jpg", "content_type": "image/jpeg", "size_bytes": len(jpeg)},
        )
    ).json()["data"]
    put = await api_client.put(up["upload_url"].replace("http://it", ""), content=jpeg.tobytes(), headers=up["upload_headers"])
    assert put.status_code == 200, put.text
    done = await api_client.post(
        f"/api/v1/inspections/{insp_id}/media/complete",
        json={"storage_path": up["storage_path"], "storage_bucket": up["storage_bucket"], "media_type": "IMAGE",
              "mime_type": "image/jpeg", "size_bytes": len(jpeg)},
    )
    assert done.status_code == 201, done.text
    assert (await api_client.post(f"/api/v1/inspections/{insp_id}/submit")).status_code == 200

    sent = []
    monkeypatch.setattr(
        "app.api.v1.endpoints.inspections.dispatch_inspection_processing",
        lambda job_id, inspection_id, organization_id: sent.append((job_id, inspection_id, organization_id)) or str(job_id),
    )
    proc = await api_client.post(f"/api/v1/inspections/{insp_id}/process")
    assert proc.status_code == 202, proc.text
    (job_id, sent_insp, sent_org) = sent[0]

    # Execute exactly what the Celery task runs, against PostgreSQL.
    async with session_factory() as session:
        result = await execute_inspection_pipeline(session, job_id, sent_insp, sent_org, confidence_threshold=0.2)
    assert result["status"] == "COMPLETED", result
    assert result["detection_count"] >= 1

    async with session_factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT ST_AsText(d.location) AS wkt, ST_SRID(d.location) AS srid, "
                    "ST_DWithin(CAST(d.location AS geography), CAST(s.geometry AS geography), 20) AS on_segment "
                    "FROM ai_detections d JOIN inspections i ON i.id = d.inspection_id "
                    "JOIN road_segments s ON s.id = i.road_segment_id WHERE d.inspection_id = :id"
                ),
                {"id": uuid.UUID(insp_id)},
            )
        ).all()
        job_status, insp_status = (
            await session.execute(
                text("SELECT j.status, i.status FROM processing_jobs j JOIN inspections i ON i.id = j.entity_id WHERE j.id = :j"),
                {"j": job_id},
            )
        ).one()

    assert rows and all(r.wkt == "POINT(73.8525 18.5201)" and r.srid == 4326 and r.on_segment for r in rows)
    assert (job_status, insp_status) == ("COMPLETED", "ANALYZED")
    detections = await api_client.get(f"/api/v1/inspections/{insp_id}/detections")
    assert detections.json()["data"][0]["location"] == {"latitude": 18.5201, "longitude": 73.8525}


@pytest.mark.asyncio
async def test_detection_grouping_uses_postgis_geography_radius(api_client, session_factory):
    """Repeat detections of one defect within GPS drift group via ST_DWithin(geography); far ones do not."""
    from datetime import datetime, timezone

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.ai import AIDetection, AIModel, AIProcessingRun, DamageType
    from app.models.damage import DamageObservation
    from app.models.inspection import InspectionMedia
    from app.services.damage_grouping import promote_detection
    from app.services.spatial import point_to_wkt
    from tests_integration.conftest import ORG_ID

    _, (seg1, _) = await _road_with_segments(api_client)
    insp = await api_client.post(
        "/api/v1/inspections",
        json={"road_segment_id": seg1, "location": {"latitude": 18.5201, "longitude": 73.8525, "accuracy_m": 4.0}},
    )
    assert insp.status_code == 201, insp.text
    insp_id = uuid.UUID(insp.json()["data"]["id"])
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        pothole = DamageType(id=uuid.uuid4(), code="POTHOLE", name="Pothole")
        model = AIModel(id=uuid.uuid4(), name="it", model_family="yolo", model_type="detection", version="t",
                        artifact_uri="none")
        run = AIProcessingRun(id=uuid.uuid4(), organization_id=ORG_ID, model_id=model.id, inspection_id=insp_id,
                              run_type="INSPECTION", status="COMPLETED")
        session.add_all([pothole, model, run])
        det_ids = []
        # (lon offset): same point, ~3 m east, ~50 m east. Each from its own photo.
        for lon in (73.8525, 73.852528, 73.85297):
            media = InspectionMedia(
                id=uuid.uuid4(), organization_id=ORG_ID, inspection_id=insp_id, media_type="IMAGE",
                storage_bucket="b", storage_path=f"p/{uuid.uuid4()}.jpg", original_filename="r.jpg",
                mime_type="image/jpeg", file_size_bytes=1, upload_status="COMPLETED",
            )
            det = AIDetection(
                id=uuid.uuid4(), organization_id=ORG_ID, ai_processing_run_id=run.id, inspection_id=insp_id,
                media_id=media.id, damage_type_id=pothole.id, confidence=0.9, bbox_x_min=0.1, bbox_y_min=0.1,
                bbox_x_max=0.3, bbox_y_max=0.3, location=point_to_wkt(18.5201, lon),
                raw_output={"severity_assessment": {"severity": "HIGH", "score": 0.7}}, created_at=now,
            )
            session.add_all([media, det])
            det_ids.append(det.id)
        await session.commit()

    results = []
    for det_id in det_ids:
        async with session_factory() as session:
            det = (
                await session.execute(
                    select(AIDetection).where(AIDetection.id == det_id).options(selectinload(AIDetection.inspection))
                )
            ).scalar_one()
            results.append(await promote_detection(session, ORG_ID, det))

    assert [r.action for r in results] == ["CREATED", "GPS_GROUPED", "CREATED"]
    assert results[1].record.id == results[0].record.id
    assert results[2].record.id != results[0].record.id
    assert results[1].distance_meters == pytest.approx(haversine_m(18.5201, 73.8525, 18.5201, 73.852528), abs=0.05)

    async with session_factory() as session:
        again = await promote_detection(
            session, ORG_ID,
            (await session.execute(
                select(AIDetection).where(AIDetection.id == det_ids[1]).options(selectinload(AIDetection.inspection))
            )).scalar_one(),
        )
        assert again.action == "ALREADY_PROMOTED"
        counts = (
            await session.execute(
                text("SELECT observation_count FROM damage_records WHERE id = :id"), {"id": results[0].record.id}
            )
        ).scalar_one()
        observations = (await session.execute(select(DamageObservation))).scalars().all()
    assert counts == 2
    assert len(observations) == 3
