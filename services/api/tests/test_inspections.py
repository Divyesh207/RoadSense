import uuid

import pytest

from app.models.inspection import Inspection
from tests.conftest import (
    INSPECTOR_USER_ID,
    ORG_1_ID,
    ORG_2_ID,
)


async def get_token(async_client, email="inspector@example.com", password="InspectorSecret123!"):
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_inspection_success(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    payload = {
        "inspection_type": "FIELD",
        "location": {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "accuracy_m": 4.5,
        },
        "notes": "Visual road survey along expressway section A.",
    }

    resp = await async_client.post("/api/v1/inspections", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["status"] == "DRAFT"
    assert data["organization_id"] == str(ORG_1_ID)
    assert data["inspector_user_id"] == str(INSPECTOR_USER_ID)
    assert data["location"]["latitude"] == 18.5204
    assert data["location"]["longitude"] == 73.8567
    assert data["location"]["accuracy_m"] == 4.5
    assert data["notes"] == "Visual road survey along expressway section A."
    assert data["media_summary"]["media_count"] == 0


@pytest.mark.asyncio
async def test_create_inspection_with_road_and_segment(async_client):
    # Authority creates road and segment
    auth_token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    auth_headers = {"Authorization": f"Bearer {auth_token}", "X-Organization-ID": str(ORG_1_ID)}

    road_resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "Survey Road", "road_code": "SR-100"},
        headers=auth_headers,
    )
    road_id = road_resp.json()["data"]["id"]

    seg_resp = await async_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={"segment_number": 1, "name": "Survey Segment 1"},
        headers=auth_headers,
    )
    seg_id = seg_resp.json()["data"]["id"]

    # Inspector creates inspection on this road and segment
    insp_token = await get_token(async_client)
    insp_headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}

    insp_resp = await async_client.post(
        "/api/v1/inspections",
        json={
            "road_id": road_id,
            "road_segment_id": seg_id,
            "location": {"latitude": 18.5210, "longitude": 73.8570},
            "notes": "Inspecting segment 1",
        },
        headers=insp_headers,
    )
    assert insp_resp.status_code == 201
    insp_data = insp_resp.json()["data"]
    assert insp_data["road_id"] == road_id
    assert insp_data["road_segment_id"] == seg_id


@pytest.mark.asyncio
async def test_create_inspection_offline_idempotent(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    client_device_id = uuid.uuid4()
    payload = {
        "client_id": str(client_device_id),
        "location": {"latitude": 18.5220, "longitude": 73.8580},
        "notes": "Offline captured inspection",
    }

    # First attempt (sync 1)
    resp1 = await async_client.post("/api/v1/inspections", json=payload, headers=headers)
    assert resp1.status_code == 201
    id1 = resp1.json()["data"]["id"]

    # Second attempt with same client_id (sync retry)
    resp2 = await async_client.post("/api/v1/inspections", json=payload, headers=headers)
    assert resp2.status_code == 200
    id2 = resp2.json()["data"]["id"]

    # Idempotent: must return the exact same inspection
    assert id1 == id2


@pytest.mark.asyncio
async def test_list_inspections_and_filter(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create two inspections
    await async_client.post("/api/v1/inspections", json={"notes": "Inspection Alpha"}, headers=headers)
    await async_client.post("/api/v1/inspections", json={"notes": "Inspection Beta"}, headers=headers)

    # List
    list_resp = await async_client.get("/api/v1/inspections", headers=headers)
    assert list_resp.status_code == 200
    res = list_resp.json()
    assert res["success"] is True
    assert res["meta"]["total_count"] >= 2
    assert len(res["data"]) >= 2

    # Filter by status
    filter_resp = await async_client.get("/api/v1/inspections?status=DRAFT", headers=headers)
    assert filter_resp.status_code == 200
    assert all(i["status"] == "DRAFT" for i in filter_resp.json()["data"])


@pytest.mark.asyncio
async def test_get_and_update_inspection(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create
    create_resp = await async_client.post(
        "/api/v1/inspections",
        json={"notes": "Initial field notes"},
        headers=headers,
    )
    insp_id = create_resp.json()["data"]["id"]

    # Get
    get_resp = await async_client.get(f"/api/v1/inspections/{insp_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["notes"] == "Initial field notes"

    # Update
    update_resp = await async_client.patch(
        f"/api/v1/inspections/{insp_id}",
        json={"notes": "Updated field notes after second walkthrough"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["notes"] == "Updated field notes after second walkthrough"


@pytest.mark.asyncio
async def test_submit_inspection_state_transition(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create DRAFT
    create_resp = await async_client.post("/api/v1/inspections", json={"notes": "To be submitted"}, headers=headers)
    insp_id = create_resp.json()["data"]["id"]

    # Submit inspection -> transitions to SUBMITTED
    sub_resp = await async_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert sub_resp.status_code == 200
    assert sub_resp.json()["data"]["status"] == "SUBMITTED"
    assert sub_resp.json()["data"]["submitted_at"] is not None

    # Invalid state transition: submitting already SUBMITTED inspection -> 409 INVALID_STATE_TRANSITION
    resubmit_resp = await async_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)
    assert resubmit_resp.status_code == 409
    assert resubmit_resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


@pytest.mark.asyncio
async def test_media_upload_lifecycle(async_client):
    token = await get_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create inspection
    insp_resp = await async_client.post("/api/v1/inspections", json={"notes": "Media test"}, headers=headers)
    insp_id = insp_resp.json()["data"]["id"]

    # 1. Request presigned upload URL
    upload_url_req = {
        "filename": "pothole_survey_front.mp4",
        "content_type": "video/mp4",
        "size_bytes": 10485760,  # 10 MB
        "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    url_resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/upload-url",
        json=upload_url_req,
        headers=headers,
    )
    assert url_resp.status_code == 200
    url_data = url_resp.json()["data"]
    assert "upload_url" in url_data
    assert "storage_path" in url_data
    assert url_data["expires_in"] == 900
    storage_path = url_data["storage_path"]

    # 2. Complete upload
    complete_req = {
        "storage_path": storage_path,
        "storage_bucket": "inspection-media",
        "media_type": "VIDEO",
        "mime_type": "video/mp4",
        "size_bytes": 10485760,
        "original_filename": "pothole_survey_front.mp4",
        "duration_seconds": 60.5,
        "width_px": 1920,
        "height_px": 1080,
        "location": {"latitude": 18.5204, "longitude": 73.8567},
    }
    complete_resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/complete",
        json=complete_req,
        headers=headers,
    )
    assert complete_resp.status_code == 201
    media_data = complete_resp.json()["data"]
    assert media_data["media_type"] == "VIDEO"
    assert media_data["upload_status"] == "COMPLETED"
    assert media_data["storage_path"] == storage_path

    # Verify inspection status transitioned to UPLOADING and media summary reflects it
    get_insp = await async_client.get(f"/api/v1/inspections/{insp_id}", headers=headers)
    assert get_insp.json()["data"]["status"] == "UPLOADING"
    assert get_insp.json()["data"]["media_summary"]["video_count"] == 1

    # 3. List media
    list_media_resp = await async_client.get(f"/api/v1/inspections/{insp_id}/media", headers=headers)
    assert list_media_resp.status_code == 200
    media_list = list_media_resp.json()["data"]
    assert len(media_list) == 1
    assert media_list[0]["storage_path"] == storage_path


@pytest.mark.asyncio
async def test_process_inspection_and_job_lifecycle(async_client, monkeypatch):
    dispatched = []
    monkeypatch.setattr(
        "app.api.v1.endpoints.inspections.dispatch_inspection_processing",
        lambda job_id, inspection_id, organization_id: dispatched.append(job_id) or str(job_id),
    )
    # Authority user has inspections:process permission
    auth_token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    headers = {"Authorization": f"Bearer {auth_token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create inspection with one uploaded image, then submit
    insp_resp = await async_client.post("/api/v1/inspections", json={"notes": "Ready for AI analysis"}, headers=headers)
    insp_id = insp_resp.json()["data"]["id"]
    media_resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/complete",
        json={
            "storage_path": f"inspections/{insp_id}/road.jpg",
            "media_type": "IMAGE",
            "mime_type": "image/jpeg",
            "size_bytes": 2048,
        },
        headers=headers,
    )
    assert media_resp.status_code == 201

    # 1. Attempting to process in DRAFT state -> 409 INVALID_STATE_TRANSITION
    premature_proc = await async_client.post(f"/api/v1/inspections/{insp_id}/process", headers=headers)
    assert premature_proc.status_code == 409
    assert premature_proc.json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    # Submit
    await async_client.post(f"/api/v1/inspections/{insp_id}/submit", headers=headers)

    # 2. Trigger asynchronous AI processing
    proc_resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/process",
        headers={**headers, "Idempotency-Key": f"test_idemp_{insp_id}"},
    )
    assert proc_resp.status_code == 202
    proc_data = proc_resp.json()["data"]
    job_id = proc_data["job_id"]
    assert proc_data["status"] == "QUEUED"
    assert proc_data["inspection_id"] == insp_id
    assert [str(j) for j in dispatched] == [job_id]

    # Verify inspection state is now PROCESSING
    insp_check = await async_client.get(f"/api/v1/inspections/{insp_id}", headers=headers)
    assert insp_check.json()["data"]["status"] == "PROCESSING"

    # 3. Check job status endpoint GET /api/v1/jobs/{job_id}
    job_resp = await async_client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_resp.status_code == 200
    job_data = job_resp.json()["data"]
    assert job_data["id"] == job_id
    assert job_data["status"] == "QUEUED"
    assert job_data["job_type"] == "INSPECTION_AI_ANALYSIS"
    assert job_data["entity_id"] == insp_id


@pytest.mark.asyncio
async def test_inspection_multi_tenant_isolation(async_client, db_session):
    auth_token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    headers_org1 = {"Authorization": f"Bearer {auth_token}", "X-Organization-ID": str(ORG_1_ID)}

    # Direct DB seed inspection in Org 2
    org2_insp = Inspection(
        id=uuid.uuid4(),
        organization_id=ORG_2_ID,
        inspector_user_id=INSPECTOR_USER_ID,
        status="DRAFT",
        source="FIELD",
    )
    db_session.add(org2_insp)
    await db_session.commit()

    # User in Org 1 accessing Org 2 inspection -> 403 ORGANIZATION_ACCESS_DENIED
    forbidden_get = await async_client.get(f"/api/v1/inspections/{org2_insp.id}", headers=headers_org1)
    assert forbidden_get.status_code == 403
    assert forbidden_get.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    forbidden_submit = await async_client.post(f"/api/v1/inspections/{org2_insp.id}/submit", headers=headers_org1)
    assert forbidden_submit.status_code == 403
    assert forbidden_submit.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"


@pytest.mark.asyncio
async def test_inspection_rbac_permissions(async_client):
    # Crew user lacks inspections:create permission
    crew_token = await get_token(async_client, email="crew@example.com", password="CrewSecret123!")
    headers = {"Authorization": f"Bearer {crew_token}", "X-Organization-ID": str(ORG_1_ID)}

    resp = await async_client.post("/api/v1/inspections", json={"notes": "Unauthorized"}, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
