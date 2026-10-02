import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.ai import DamageType
from app.models.damage import DamageRecord
from tests.conftest import (
    ADMIN_USER_ID,
    AUTHORITY_USER_ID,
    CREW_USER_ID,
    INSPECTOR_USER_ID,
    ORG_1_ID,
)


@pytest.fixture
def auth_headers():
    def _get(user_id: uuid.UUID, org_id: uuid.UUID = ORG_1_ID):
        token, _ = create_access_token(user_id)
        return {
            "Authorization": f"Bearer {token}",
            "X-Organization-ID": str(org_id),
            "X-Bypass-Rate-Limit": "test-bypass",
        }

    return _get


@pytest.mark.asyncio
async def test_master_platform_e2e_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers,
):
    """
    Master End-to-End Validation Scenario (Roadmap Phase 17 / Section 21)
    Validates complete lifecycle from Road Creation -> Field Inspection -> AI Inference
    -> Human Review -> Maintenance Dispatch -> Repair Evidence -> Verification -> Reporting.
    """
    admin_hdr = auth_headers(ADMIN_USER_ID)
    auth_hdr = auth_headers(AUTHORITY_USER_ID)
    insp_hdr = auth_headers(INSPECTOR_USER_ID)
    crew_hdr = auth_headers(CREW_USER_ID)

    # -------------------------------------------------------------
    # Step 1: Road & Segment Management
    # -------------------------------------------------------------
    road_payload = {
        "name": "Expressway E2E Arterial",
        "road_code": "EXP-E2E-001",
        "road_type": "HIGHWAY",
        "administrative_area": "Pune Metro",
        "geometry": {
            "type": "LineString",
            "coordinates": [[73.8567, 18.5204], [73.8570, 18.5210], [73.8580, 18.5220]],
        },
    }
    road_resp = await async_client.post("/api/v1/roads", json=road_payload, headers=auth_hdr)
    assert road_resp.status_code == 201, road_resp.text
    road_data = road_resp.json()["data"]
    road_id = road_data["id"]

    seg_payload = {
        "segment_number": 1,
        "name": "Segment 1 - South Terminal",
        "start_chainage": 0.0,
        "end_chainage": 500.0,
        "length_meters": 500.0,
        "lane_count": 4,
        "surface_type": "ASPHALT",
        "speed_limit_kph": 100,
        "geometry": {
            "type": "LineString",
            "coordinates": [[73.8567, 18.5204], [73.8570, 18.5210]],
        },
    }
    seg_resp = await async_client.post(f"/api/v1/roads/{road_id}/segments", json=seg_payload, headers=auth_hdr)
    assert seg_resp.status_code == 201, seg_resp.text
    seg_data = seg_resp.json()["data"]
    segment_id = seg_data["id"]

    # -------------------------------------------------------------
    # Step 2: Field Inspector Submits Inspection
    # -------------------------------------------------------------
    insp_payload = {
        "road_id": road_id,
        "road_segment_id": segment_id,
        "notes": "E2E Field inspection routine run",
        "location": {"latitude": 18.5206, "longitude": 73.8568},
    }
    insp_resp = await async_client.post("/api/v1/inspections", json=insp_payload, headers=insp_hdr)
    assert insp_resp.status_code == 201, insp_resp.text
    insp_data = insp_resp.json()["data"]
    inspection_id = insp_data["id"]

    # Request upload URL
    upload_url_req = {
        "filename": "media_001.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 1048576,
        "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    url_resp = await async_client.post(
        f"/api/v1/inspections/{inspection_id}/media/upload-url",
        json=upload_url_req,
        headers=insp_hdr,
    )
    assert url_resp.status_code == 200, url_resp.text
    storage_path = url_resp.json()["data"]["storage_path"]

    # Complete upload
    complete_req = {
        "storage_path": storage_path,
        "storage_bucket": "inspection-media",
        "media_type": "IMAGE",
        "mime_type": "image/jpeg",
        "size_bytes": 1048576,
        "original_filename": "media_001.jpg",
        "location": {"latitude": 18.5206, "longitude": 73.8568},
    }
    complete_resp = await async_client.post(
        f"/api/v1/inspections/{inspection_id}/media/complete",
        json=complete_req,
        headers=insp_hdr,
    )
    assert complete_resp.status_code == 201, complete_resp.text

    # Submit inspection
    sub_resp = await async_client.post(f"/api/v1/inspections/{inspection_id}/submit", headers=insp_hdr)
    assert sub_resp.status_code == 200, sub_resp.text

    # -------------------------------------------------------------
    # Step 3: AI Inference & Detection Pipeline
    # -------------------------------------------------------------
    # Obtain pothole damage type
    dt_res = await db_session.execute(select(DamageType).where(DamageType.code == "POTHOLE"))
    pothole_dt = dt_res.scalar_one_or_none()
    if not pothole_dt:
        pothole_dt = DamageType(
            id=uuid.uuid4(),
            code="POTHOLE",
            name="Pothole",
            category="SURFACE",
            severity_default="HIGH",
            standard_code="IRC:82-2015",
            is_active=True,
        )
        db_session.add(pothole_dt)
        await db_session.flush()

    # Create candidate damage record detected by pipeline
    damage_record = DamageRecord(
        id=uuid.uuid4(),
        organization_id=ORG_1_ID,
        inspection_id=uuid.UUID(inspection_id),
        road_id=uuid.UUID(road_id),
        road_segment_id=uuid.UUID(segment_id),
        damage_type_id=pothole_dt.id,
        source_type="AI",
        severity="HIGH",
        severity_score=0.88,
        status="PENDING_REVIEW",
        confidence=0.88,
        estimated_area_m2=0.55,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(damage_record)
    await db_session.commit()
    damage_id = damage_record.id

    # -------------------------------------------------------------
    # Step 4: Human Review & Damage Confirmation
    # -------------------------------------------------------------
    review_payload = {
        "decision": "CONFIRMED",
        "damage_type_id": str(pothole_dt.id),
        "severity": "HIGH",
        "notes": "Confirmed severe pothole requiring urgent repair.",
    }
    review_resp = await async_client.post(
        f"/api/v1/damages/{damage_id}/review", json=review_payload, headers=auth_hdr
    )
    assert review_resp.status_code == 200, review_resp.text
    reviewed_damage = review_resp.json()["data"]
    assert reviewed_damage["status"] == "CONFIRMED"

    # -------------------------------------------------------------
    # Step 5: Road Health Assessment
    # -------------------------------------------------------------
    health_resp = await async_client.get(f"/api/v1/road-segments/{segment_id}/health", headers=auth_hdr)
    assert health_resp.status_code == 200, health_resp.text
    health_data = health_resp.json()["data"]
    assert "health_score" in health_data

    # -------------------------------------------------------------
    # Step 6: Maintenance Job Creation & Contractor Dispatch
    # -------------------------------------------------------------
    job_payload = {
        "title": "Emergency Patch on Expressway",
        "road_segment_id": segment_id,
        "damage_record_ids": [str(damage_id)],
        "job_type": "EMERGENCY_PATCH",
        "priority": "HIGH",
        "description": "Urgent pothole filling on Northbound lane",
        "scheduled_start_date": datetime.now(timezone.utc).isoformat(),
    }
    job_create_resp = await async_client.post("/api/v1/maintenance-jobs", json=job_payload, headers=auth_hdr)
    assert job_create_resp.status_code == 201, job_create_resp.text
    job_id = job_create_resp.json()["data"]["id"]

    # Assign job to maintenance crew
    assign_payload = {
        "assigned_to_user_id": str(CREW_USER_ID),
        "notes": "Assigned to primary roadworks crew",
    }
    assign_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/assign", json=assign_payload, headers=auth_hdr
    )
    assert assign_resp.status_code == 200, assign_resp.text

    # Contractor transitions status: ASSIGNED -> IN_PROGRESS -> COMPLETED
    status_prog_payload = {
        "status": "IN_PROGRESS",
        "notes": "Crew mobilized on site with asphalt mixer",
    }
    st_prog_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status", json=status_prog_payload, headers=crew_hdr
    )
    assert st_prog_resp.status_code == 200, st_prog_resp.text

    status_comp_payload = {
        "status": "COMPLETED",
        "notes": "Hot mix asphalt patching completed and compacted",
    }
    st_comp_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/status", json=status_comp_payload, headers=crew_hdr
    )
    assert st_comp_resp.status_code == 200, st_comp_resp.text
    assert st_comp_resp.json()["data"]["status"] == "COMPLETED"

    # -------------------------------------------------------------
    # Step 7: Repair Evidence Submission & Verification
    # -------------------------------------------------------------
    ev_url_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/upload-url",
        json={"filename": "evidence_post_patch.jpg", "content_type": "image/jpeg", "size_bytes": 4},
        headers=crew_hdr,
    )
    assert ev_url_resp.status_code == 200, ev_url_resp.text
    ev_upload = ev_url_resp.json()["data"]
    put_resp = await async_client.put(
        ev_upload["upload_url"].replace("http://testserver", ""),
        content=b"\xff\xd8\xff\xd9",
        headers=ev_upload["upload_headers"],
    )
    assert put_resp.status_code == 200, put_resp.text

    evidence_payload = {
        "media_type": "IMAGE",
        "storage_bucket": ev_upload["storage_bucket"],
        "storage_path": ev_upload["storage_path"],
        "latitude": 18.5206,
        "longitude": 73.8568,
        "notes": "Photo of freshly completed patch",
    }
    ev_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/repair-evidence/complete", json=evidence_payload, headers=crew_hdr
    )
    assert ev_resp.status_code in [200, 201], ev_resp.text

    verify_payload = {
        "decision": "VERIFIED",
        "notes": "Verified surface smoothness and adequate compaction.",
    }
    verify_resp = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/verify", json=verify_payload, headers=auth_hdr
    )
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["data"]["verification_status"] == "VERIFIED"

    # -------------------------------------------------------------
    # Step 8: Analytics & Operational Reporting
    # -------------------------------------------------------------
    analytics_resp = await async_client.get("/api/v1/dashboard/summary", headers=auth_hdr)
    assert analytics_resp.status_code == 200, analytics_resp.text
    dash_summary = analytics_resp.json()["data"]
    assert dash_summary["total_roads"] >= 1
    assert dash_summary["verified_repairs"] >= 1

    report_payload = {
        "report_type": "EXECUTIVE_ROAD_CONDITION",
        "parameters": {"road_id": road_id},
    }
    report_resp = await async_client.post("/api/v1/reports", json=report_payload, headers=auth_hdr)
    assert report_resp.status_code == 202, report_resp.text
    report_id = report_resp.json()["data"]["report_id"]

    # Verify report is listed and has download url
    report_get_resp = await async_client.get(f"/api/v1/reports/{report_id}", headers=auth_hdr)
    assert report_get_resp.status_code == 200, report_get_resp.text

    url_resp = await async_client.get(f"/api/v1/reports/{report_id}/download-url", headers=auth_hdr)
    assert url_resp.status_code == 200, url_resp.text
    assert "download_url" in url_resp.json()["data"]

    # -------------------------------------------------------------
    # Step 9: Role Violation & Unauthorized Operation Checks
    # -------------------------------------------------------------
    # Contractor attempts to create a road -> 403 Forbidden
    unauth_road = await async_client.post("/api/v1/roads", json=road_payload, headers=crew_hdr)
    assert unauth_road.status_code == 403

    # Field Inspector attempts to verify a repair -> 403 Forbidden
    unauth_verify = await async_client.post(
        f"/api/v1/maintenance-jobs/{job_id}/verify", json=verify_payload, headers=insp_hdr
    )
    assert unauth_verify.status_code == 403

    # -------------------------------------------------------------
    # Step 10: Complete Audit Trail Traceability
    # -------------------------------------------------------------
    audit_resp = await async_client.get("/api/v1/audit-logs", headers=admin_hdr)
    assert audit_resp.status_code == 200, audit_resp.text
    assert audit_resp.json()["meta"]["total_count"] >= 1
