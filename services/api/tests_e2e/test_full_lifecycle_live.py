"""
Full lifecycle E2E against the running Docker stack (API + Celery worker + trained YOLO +
PostGIS). SOFTWARE validation only: it proves the records stay linked through the whole
lifecycle. It does not measure real-world detection or repair-verification accuracy (the
AFTER image is a constructed, inpainted copy of the BEFORE photo).

Opt-in; skipped unless configured:
    E2E_API_URL=http://localhost:8000/api/v1
    E2E_EMAIL=... E2E_PASSWORD=...            (an existing local test account)
    E2E_IMAGE=path/to/road_photo.jpg          (e.g. an RDD2022 India test image with potholes)
    E2E_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5433/road_platform   (for cleanup)
    E2E_DOCKER_CLEANUP=1                       (optional: delete uploaded files in the api container)
    E2E_LOCAL_STORAGE_VIA_API=1                (optional: when PUBLIC_API_BASE_URL is a LAN address this
                                                machine cannot reach, send local-storage signed URLs to
                                                E2E_API_URL's origin instead; signatures are unchanged)

Everything it creates lives on its own road (name carries a unique marker) and is deleted
at the end, pass or fail. Audit log entries are kept.
"""

import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

API = os.getenv("E2E_API_URL", "")
IMAGE = Path(os.getenv("E2E_IMAGE", ""))
pytestmark = pytest.mark.skipif(
    not (API and os.getenv("E2E_EMAIL") and os.getenv("E2E_PASSWORD") and IMAGE.is_file() and os.getenv("E2E_DATABASE_URL")),
    reason="live E2E not configured (see module docstring)",
)

LAT, LON = 18.5500, 73.8800
DRIFT = 0.000028  # ~3 m of longitude here

CLEANUP_SQL = """
create temp table t_road as select id from roads where id = %(road)s and name like %(marker)s;
create temp table t_insp as select id from inspections where road_id in (select id from t_road);
create temp table t_job as select id from maintenance_jobs where road_id in (select id from t_road);
create temp table t_dmg as select id from damage_records where road_id in (select id from t_road);
create temp table t_pj as select id from processing_jobs
  where entity_id in (select id from t_insp) or entity_id in (select id from t_job);
create temp table t_run as select id from ai_processing_runs
  where inspection_id in (select id from t_insp) or processing_job_id in (select id from t_pj);
select storage_bucket || '/' || storage_path from repair_evidence where maintenance_job_id in (select id from t_job)
union all select storage_bucket || '/' || storage_path from inspection_media where inspection_id in (select id from t_insp);
"""
DELETE_SQL = """
delete from recurrence_records where new_damage_id in (select id from t_dmg) or historical_damage_id in (select id from t_dmg);
delete from repair_verifications where maintenance_job_id in (select id from t_job);
delete from repair_evidence where maintenance_job_id in (select id from t_job);
delete from maintenance_status_history where maintenance_job_id in (select id from t_job);
delete from maintenance_damage_links where maintenance_job_id in (select id from t_job);
delete from maintenance_jobs where id in (select id from t_job);
delete from damage_reviews where damage_record_id in (select id from t_dmg);
delete from damage_observations where damage_record_id in (select id from t_dmg) or inspection_id in (select id from t_insp);
delete from damage_records where id in (select id from t_dmg);
delete from ai_detections where inspection_id in (select id from t_insp) or ai_processing_run_id in (select id from t_run);
delete from ai_processing_runs where id in (select id from t_run);
delete from processing_jobs where id in (select id from t_pj);
delete from inspection_media where inspection_id in (select id from t_insp);
delete from inspections where id in (select id from t_insp);
delete from deterioration_predictions where road_id in (select id from t_road);
delete from road_health_snapshots where road_id in (select id from t_road);
delete from road_segments where road_id in (select id from t_road);
delete from roads where id in (select id from t_road);
"""


def signed(url: str) -> str:
    if os.getenv("E2E_LOCAL_STORAGE_VIA_API") == "1" and "/storage/local/" in url:
        from urllib.parse import urlsplit

        api = urlsplit(API)
        parts = urlsplit(url)
        return f"{api.scheme}://{api.netloc}{parts.path}" + (f"?{parts.query}" if parts.query else "")
    return url


def cleanup(road_id: str, marker: str) -> list[str]:
    import psycopg2

    conn = psycopg2.connect(os.environ["E2E_DATABASE_URL"])
    try:
        with conn, conn.cursor() as cur:
            cur.execute(CLEANUP_SQL, {"road": road_id, "marker": marker + "%"})
            files = [r[0] for r in cur.fetchall()]
            cur.execute(DELETE_SQL)
    finally:
        conn.close()
    if os.getenv("E2E_DOCKER_CLEANUP") == "1" and files:
        script = "; ".join(f'rm -f "/data/media/{f}"; rmdir "$(dirname "/data/media/{f}")" 2>/dev/null' for f in files)
        subprocess.run(["docker", "compose", "exec", "-T", "-u", "root", "api", "sh", "-c", script + "; true"], check=False)
    return files


def test_full_lifecycle_live():
    import cv2
    import httpx
    import numpy as np

    marker = f"E2E lifecycle {uuid.uuid4().hex[:8]}"
    c = httpx.Client(timeout=60)
    tok = c.post(f"{API}/auth/login", json={"email": os.environ["E2E_EMAIL"], "password": os.environ["E2E_PASSWORD"]})
    assert tok.status_code == 200, "authentication"
    token = tok.json()["data"]["access_token"]
    me = c.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["data"]
    H = {"Authorization": f"Bearer {token}", "X-Organization-ID": me["organizations"][0]["organization_id"]}

    road = c.post(f"{API}/roads", headers=H, json={
        "name": marker, "road_type": "URBAN",
        "geometry": {"type": "LineString", "coordinates": [[LON - 0.001, LAT], [LON + 0.001, LAT]]}})
    assert road.status_code == 201, road.text
    road_id = road.json()["data"]["id"]
    try:
        seg = c.post(f"{API}/roads/{road_id}/segments", headers=H, json={
            "segment_number": 1, "name": "E2E S1",
            "geometry": {"type": "LineString", "coordinates": [[LON - 0.001, LAT], [LON + 0.001, LAT]]}})
        assert seg.status_code == 201, seg.text
        seg_id = seg.json()["data"]["id"]

        def inspect(lon: float, data: bytes) -> list[dict]:
            insp = c.post(f"{API}/inspections", headers=H, json={
                "road_id": road_id, "road_segment_id": seg_id, "notes": marker,
                "location": {"latitude": LAT, "longitude": lon}}).json()["data"]
            up = c.post(f"{API}/inspections/{insp['id']}/media/upload-url", headers=H,
                        json={"filename": "road.jpg", "content_type": "image/jpeg", "size_bytes": len(data)}).json()["data"]
            assert c.put(signed(up["upload_url"]), content=data, headers={"Content-Type": "image/jpeg"}).status_code in (200, 201, 204)
            done = c.post(f"{API}/inspections/{insp['id']}/media/complete", headers=H, json={
                "storage_path": up["storage_path"], "storage_bucket": up["storage_bucket"], "media_type": "IMAGE",
                "mime_type": "image/jpeg", "size_bytes": len(data), "location": {"latitude": LAT, "longitude": lon}})
            assert done.status_code == 201, done.text
            assert c.post(f"{API}/inspections/{insp['id']}/submit", headers=H).status_code == 200
            job_id = c.post(f"{API}/inspections/{insp['id']}/process", headers=H).json()["data"]["job_id"]
            for _ in range(120):
                job = c.get(f"{API}/jobs/{job_id}", headers=H).json()["data"]
                if job["status"] in ("COMPLETED", "FAILED", "DEAD_LETTER"):
                    break
                time.sleep(2)
            assert job["status"] == "COMPLETED", f"Celery processing: {job}"
            dets = c.get(f"{API}/inspections/{insp['id']}/detections", headers=H).json()["data"]
            assert dets, "trained model found no damage in E2E_IMAGE; use a photo with visible potholes"
            assert all(d["detection_method"] == "TRAINED_MODEL" for d in dets), "heuristic fallback must not be used"
            return dets

        photo = IMAGE.read_bytes()
        dets1 = inspect(LON, photo)
        pothole = max((d for d in dets1 if d["damage_type"] == "POTHOLE"), key=lambda d: d["confidence"], default=dets1[0])

        # Damage persistence + PostGIS GPS grouping (second visit ~3 m away).
        rec = c.post(f"{API}/damages/from-detection/{pothole['id']}", headers=H).json()["data"]
        assert rec["status"] == "PENDING_REVIEW"
        dets2 = inspect(LON + DRIFT, photo)
        same = next(d for d in dets2 if d["damage_type"] == pothole["damage_type"])
        grouped = c.post(f"{API}/damages/from-detection/{same['id']}", headers=H).json()["data"]
        assert grouped["id"] == rec["id"] and grouped["observation_count"] >= 2, "GPS grouping"

        # Review -> health.
        assert c.post(f"{API}/damages/{rec['id']}/review", headers=H, json={"decision": "CONFIRMED", "severity": "HIGH"}).status_code == 200
        health = c.get(f"{API}/road-segments/{seg_id}/health", headers=H).json()["data"]
        assert health["health_score"] is not None and health["health_score"] < 100

        # Rule-based estimate -> priority.
        est = c.post(f"{API}/road-segments/{seg_id}/predictions", headers=H, json={"prediction_horizon_days": 90}).json()["data"]
        assert est["status"] == "GENERATED" and est["estimation_method"] == "RULE_BASED_ESTIMATE" and est["confidence"] is None
        job = c.post(f"{API}/maintenance-jobs", headers=H, json={
            "title": marker, "road_id": road_id, "road_segment_id": seg_id, "damage_record_ids": [rec["id"]]}).json()["data"]
        comps = job["priority_factors"]["components"]
        assert job["priority_factors"]["mode"] == "AUTO" and comps["deterioration_estimate"] > 0

        # Maintenance workflow with assignment.
        users = c.get(f"{API}/maintenance-jobs/assignees", headers=H).json()["data"]["users"]
        me_user = next(u for u in users if u["email"] == os.environ["E2E_EMAIL"])
        assert c.post(f"{API}/maintenance-jobs/{job['id']}/assign", headers=H, json={"assigned_to_user_id": me_user["id"]}).status_code == 200
        assert c.post(f"{API}/maintenance-jobs/{job['id']}/status", headers=H, json={"status": "VERIFIED"}).status_code == 400
        for st in ("IN_PROGRESS", "COMPLETED"):
            assert c.post(f"{API}/maintenance-jobs/{job['id']}/status", headers=H, json={"status": st}).status_code == 200

        # Repair evidence (constructed AFTER image) -> automated verification -> human review.
        img = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        for d in dets1:
            b = d["bbox"]
            cv2.rectangle(mask, (int(b["x_min"] * w) - 6, int(b["y_min"] * h) - 6),
                          (int(b["x_max"] * w) + 6, int(b["y_max"] * h) + 6), 255, -1)
        after = cv2.imencode(".jpg", cv2.inpaint(img, mask, 9, cv2.INPAINT_TELEA))[1].tobytes()
        su = c.post(f"{API}/maintenance-jobs/{job['id']}/repair-evidence/upload-url", headers=H, json={
            "filename": "after.jpg", "content_type": "image/jpeg", "size_bytes": len(after), "evidence_type": "AFTER_REPAIR"}).json()["data"]
        assert c.put(signed(su["upload_url"]), content=after, headers=su["upload_headers"]).status_code in (200, 201, 204)
        ev = c.post(f"{API}/maintenance-jobs/{job['id']}/repair-evidence/complete", headers=H, json={
            "storage_path": su["storage_path"], "storage_bucket": su["storage_bucket"], "evidence_type": "AFTER_REPAIR",
            "media_type": "IMAGE", "mime_type": "image/jpeg", "file_size_bytes": len(after), "notes": f"{marker} SYNTHETIC"})
        assert ev.status_code == 201, ev.text
        ver = c.post(f"{API}/maintenance-jobs/{job['id']}/repair-verifications", headers=H, json={}).json()["data"]
        for _ in range(90):
            vs = c.get(f"{API}/maintenance-jobs/{job['id']}/verifications", headers=H).json()["data"]
            ver = next(v for v in vs if v["id"] == ver["id"])
            if ver["verification_status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(2)
        assert ver["verification_status"] == "COMPLETED", ver
        assert ver["result"] in ("SUCCESSFUL", "SUBSTANDARD", "UNRESOLVED") and ver["model_name"]
        review = c.post(f"{API}/maintenance-jobs/{job['id']}/repair-verifications/{ver['id']}/review", headers=H,
                        json={"decision": "CONFIRMED", "notes": marker})
        assert review.status_code == 201 and review.json()["data"]["previous_result"] == ver["result"]
        status_now = c.get(f"{API}/maintenance-jobs/{job['id']}", headers=H).json()["data"]["status"]
        expected = {"SUCCESSFUL": "VERIFIED", "SUBSTANDARD": "REJECTED", "UNRESOLVED": "VERIFICATION_PENDING"}[ver["result"]]
        assert status_now == expected

        # Recurrence monitoring: only meaningful once the repair was resolved.
        if ver["result"] == "SUCCESSFUL":
            dets3 = inspect(LON + DRIFT, photo)
            again = next(d for d in dets3 if d["damage_type"] == pothole["damage_type"])
            new = c.post(f"{API}/damages/from-detection/{again['id']}", headers=H).json()["data"]
            assert new["id"] != rec["id"], "a repaired record is not reused"
            assert c.post(f"{API}/damages/{new['id']}/review", headers=H, json={"decision": "CONFIRMED"}).status_code == 200
            recs = c.get(f"{API}/analytics/recurrences", headers=H).json()["data"]
            r = next(x for x in recs if x["new_damage_id"] == new["id"])
            assert r["historical_damage_id"] == rec["id"] and r["previous_verification_result"] == "SUCCESSFUL"

        # Dashboard / historical road intelligence retrieval.
        intel = c.get(f"{API}/roads/{road_id}/intelligence", headers=H).json()["data"]
        kinds = {e["type"] for e in intel["timeline"]}
        assert {"INSPECTION", "DAMAGE", "DAMAGE_REVIEW", "HEALTH", "PRIORITY", "MAINTENANCE", "REPAIR_EVIDENCE",
                "VERIFICATION"} <= kinds
        assert c.get(f"{API}/dashboard/summary", headers=H).status_code == 200
        assert any(p["job_id"] == job["id"] for p in c.get(f"{API}/analytics/priorities", headers=H).json()["data"]) or \
            status_now == "VERIFIED"
        print(f"\nE2E lifecycle OK: verification={ver['result']} reason={ver['findings'].get('reason_code')} timeline={sorted(kinds)}")
    finally:
        files = cleanup(road_id, marker)
        print(f"cleaned up road {road_id} ({len(files)} stored file(s))")
