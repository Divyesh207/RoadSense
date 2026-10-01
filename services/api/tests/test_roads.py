import uuid

import pytest
from app.models.road import Road

from tests.conftest import ORG_1_ID, ORG_2_ID


async def get_auth_token(async_client, email="authority@example.com", password="AuthoritySecret123!"):
    resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_road_with_geometry(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    payload = {
        "name": "Mumbai-Pune Expressway",
        "road_code": "MPE-01",
        "road_type": "HIGHWAY",
        "administrative_area": "Maharashtra",
        "description": "Six-lane concrete access-controlled toll expressway.",
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [73.8567, 18.5204],
                [73.8600, 18.5230],
                [73.8650, 18.5280],
            ],
        },
    }

    response = await async_client.post("/api/v1/roads", json=payload, headers=headers)
    assert response.status_code == 201
    res = response.json()
    assert res["success"] is True
    data = res["data"]
    assert data["name"] == "Mumbai-Pune Expressway"
    assert data["road_code"] == "MPE-01"
    assert data["geometry"]["type"] == "LineString"
    assert len(data["geometry"]["coordinates"]) == 3
    assert data["organization_id"] == str(ORG_1_ID)
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_road_validation_error(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Invalid: LineString with only 1 point
    invalid_payload = {
        "name": "Invalid Road",
        "geometry": {
            "type": "LineString",
            "coordinates": [[73.8567, 18.5204]],
        },
    }
    response = await async_client.post("/api/v1/roads", json=invalid_payload, headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_roads_and_search(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create road A
    await async_client.post(
        "/api/v1/roads",
        json={"name": "Pune Ring Road", "road_code": "PRR-01", "road_type": "ARTERIAL"},
        headers=headers,
    )
    # Create road B
    await async_client.post(
        "/api/v1/roads",
        json={"name": "Solapur Highway", "road_code": "SH-65", "road_type": "HIGHWAY"},
        headers=headers,
    )

    # Search by text
    search_resp = await async_client.get("/api/v1/roads?search=Solapur", headers=headers)
    assert search_resp.status_code == 200
    search_data = search_resp.json()["data"]
    assert len(search_data) == 1
    assert search_data[0]["name"] == "Solapur Highway"

    # Filter by type
    type_resp = await async_client.get("/api/v1/roads?road_type=ARTERIAL", headers=headers)
    assert type_resp.status_code == 200
    type_data = type_resp.json()["data"]
    assert any(r["name"] == "Pune Ring Road" for r in type_data)


@pytest.mark.asyncio
async def test_list_roads_bounding_box_filter(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create road with known coordinates around (18.52, 73.85)
    await async_client.post(
        "/api/v1/roads",
        json={
            "name": "Deccan Avenue",
            "road_code": "DA-10",
            "geometry": {
                "type": "LineString",
                "coordinates": [[73.8500, 18.5200], [73.8550, 18.5250]],
            },
        },
        headers=headers,
    )

    # Bounding box that contains Deccan Avenue: [18.50, 73.80, 18.55, 73.90]
    in_resp = await async_client.get(
        "/api/v1/roads?min_lat=18.50&min_lon=73.80&max_lat=18.55&max_lon=73.90",
        headers=headers,
    )
    assert in_resp.status_code == 200
    names = [r["name"] for r in in_resp.json()["data"]]
    assert "Deccan Avenue" in names

    # Disjoint Bounding Box (Mumbai area): [19.00, 72.80, 19.10, 72.90]
    out_resp = await async_client.get(
        "/api/v1/roads?min_lat=19.00&min_lon=72.80&max_lat=19.10&max_lon=72.90",
        headers=headers,
    )
    assert out_resp.status_code == 200
    out_names = [r["name"] for r in out_resp.json()["data"]]
    assert "Deccan Avenue" not in out_names


@pytest.mark.asyncio
async def test_get_and_update_road(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create
    create_resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "Old Highway", "road_code": "OH-01", "road_type": "RURAL"},
        headers=headers,
    )
    road_id = create_resp.json()["data"]["id"]

    # Get
    get_resp = await async_client.get(f"/api/v1/roads/{road_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["name"] == "Old Highway"

    # Update
    update_resp = await async_client.patch(
        f"/api/v1/roads/{road_id}",
        json={"name": "Modernized Highway", "road_type": "HIGHWAY"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "Modernized Highway"
    assert update_resp.json()["data"]["road_type"] == "HIGHWAY"


@pytest.mark.asyncio
async def test_delete_road_soft_delete(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    create_resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "Temporary Bypass", "road_code": "TB-01"},
        headers=headers,
    )
    road_id = create_resp.json()["data"]["id"]

    # Delete (soft-delete / deactivation)
    del_resp = await async_client.delete(f"/api/v1/roads/{road_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["message"] == "Road successfully deactivated."

    # Active roads list should no longer include it
    list_resp = await async_client.get("/api/v1/roads?is_active=true", headers=headers)
    active_ids = [r["id"] for r in list_resp.json()["data"]]
    assert road_id not in active_ids


@pytest.mark.asyncio
async def test_road_segments_lifecycle(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create road
    road_resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "Eastern Corridor", "road_code": "EC-01"},
        headers=headers,
    )
    road_id = road_resp.json()["data"]["id"]

    # Create Segment 1
    seg1_resp = await async_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={
            "segment_number": 1,
            "name": "Ch. 0.0 to 1.0 km",
            "start_chainage": 0.0,
            "end_chainage": 1.0,
            "length_meters": 1000.0,
            "geometry": {
                "type": "LineString",
                "coordinates": [[73.8500, 18.5200], [73.8550, 18.5200]],
            },
        },
        headers=headers,
    )
    assert seg1_resp.status_code == 201
    seg1_id = seg1_resp.json()["data"]["id"]
    assert seg1_resp.json()["data"]["segment_number"] == 1

    # Attempt to create duplicate segment_number 1 -> 409 Conflict
    dup_resp = await async_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={"segment_number": 1, "name": "Duplicate 1"},
        headers=headers,
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "DUPLICATE_SEGMENT_NUMBER"

    # Create Segment 2
    seg2_resp = await async_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={"segment_number": 2, "name": "Ch. 1.0 to 2.0 km", "length_meters": 1000.0},
        headers=headers,
    )
    assert seg2_resp.status_code == 201

    # List segments for road
    list_segs_resp = await async_client.get(f"/api/v1/roads/{road_id}/segments", headers=headers)
    assert list_segs_resp.status_code == 200
    segs = list_segs_resp.json()["data"]
    assert len(segs) == 2
    assert segs[0]["segment_number"] == 1
    assert segs[1]["segment_number"] == 2

    # Get single segment by ID
    get_seg = await async_client.get(f"/api/v1/road-segments/{seg1_id}", headers=headers)
    assert get_seg.status_code == 200
    assert get_seg.json()["data"]["name"] == "Ch. 0.0 to 1.0 km"

    # Update segment
    patch_seg = await async_client.patch(
        f"/api/v1/road-segments/{seg1_id}",
        json={"name": "Updated Ch. 0.0 to 1.0 km (Resurfaced)"},
        headers=headers,
    )
    assert patch_seg.status_code == 200
    assert patch_seg.json()["data"]["name"] == "Updated Ch. 0.0 to 1.0 km (Resurfaced)"

    # Soft delete segment
    del_seg = await async_client.delete(f"/api/v1/road-segments/{seg1_id}", headers=headers)
    assert del_seg.status_code == 200
    assert del_seg.json()["data"]["message"] == "Road segment successfully deactivated."


@pytest.mark.asyncio
async def test_gps_location_matching(async_client):
    token = await get_auth_token(async_client)
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create road with segment running along latitude 18.5200 from lon 73.8500 to 73.8600
    road_resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "FC Road", "road_code": "FCR-01"},
        headers=headers,
    )
    road_id = road_resp.json()["data"]["id"]

    await async_client.post(
        f"/api/v1/roads/{road_id}/segments",
        json={
            "segment_number": 1,
            "name": "FC Road North",
            "geometry": {
                "type": "LineString",
                "coordinates": [[73.8500, 18.5200], [73.8600, 18.5200]],
            },
        },
        headers=headers,
    )

    # 1. Test Confident Match (Point within 3 meters: 18.52002, 73.8550)
    confident_resp = await async_client.post(
        "/api/v1/roads/match-location",
        json={"latitude": 18.52002, "longitude": 73.8550, "max_distance_meters": 50.0},
        headers=headers,
    )
    assert confident_resp.status_code == 200
    res1 = confident_resp.json()["data"]
    assert res1["matched"] is True
    assert res1["best_match"]["road_name"] == "FC Road"
    assert res1["best_match"]["distance_meters"] < 5.0
    assert res1["best_match"]["confidence_score"] >= 0.90
    assert res1["is_uncertain"] is False

    # 2. Test Uncertain Match (> 25m but <= 50m: e.g. distance ~33m)
    # 0.00030 degrees latitude is ~33.2 meters
    uncertain_resp = await async_client.post(
        "/api/v1/roads/match-location",
        json={"latitude": 18.52030, "longitude": 73.8550, "max_distance_meters": 50.0},
        headers=headers,
    )
    assert uncertain_resp.status_code == 200
    res2 = uncertain_resp.json()["data"]
    assert res2["matched"] is True
    assert res2["is_uncertain"] is True
    assert "exceeds proximity certainty threshold" in res2["uncertainty_reason"]

    # 3. Test No Match (Point 200m away, exceeding 50m max radius)
    no_match_resp = await async_client.post(
        "/api/v1/roads/match-location",
        json={"latitude": 18.5250, "longitude": 73.8550, "max_distance_meters": 50.0},
        headers=headers,
    )
    assert no_match_resp.status_code == 200
    res3 = no_match_resp.json()["data"]
    assert res3["matched"] is False
    assert res3["best_match"] is None


@pytest.mark.asyncio
async def test_road_multi_tenant_isolation(async_client, db_session):
    # Authority user is in Org 1
    auth_token = await get_auth_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    headers_org1 = {"Authorization": f"Bearer {auth_token}", "X-Organization-ID": str(ORG_1_ID)}

    # Create road in Org 1
    r1 = await async_client.post(
        "/api/v1/roads",
        json={"name": "Org 1 Exclusive Road", "road_code": "O1-RD"},
        headers=headers_org1,
    )
    org1_road_id = r1.json()["data"]["id"]

    # Seed road in Org 2 directly in DB
    org2_road_id = uuid.uuid4()
    org2_road = Road(
        id=org2_road_id,
        organization_id=ORG_2_ID,
        name="Org 2 Secret Highway",
        road_code="O2-HWY",
        is_active=True,
    )
    db_session.add(org2_road)
    await db_session.commit()

    # User in Org 1 attempting to view Org 2 road -> 403 ORGANIZATION_ACCESS_DENIED
    forbidden_resp = await async_client.get(f"/api/v1/roads/{org2_road_id}", headers=headers_org1)
    assert forbidden_resp.status_code == 403
    assert forbidden_resp.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # Listing roads for Org 1 must never include Org 2's road
    list_resp = await async_client.get("/api/v1/roads", headers=headers_org1)
    ids = [r["id"] for r in list_resp.json()["data"]]
    assert str(org1_road_id) in ids
    assert str(org2_road_id) not in ids


@pytest.mark.asyncio
async def test_road_rbac_permissions(async_client):
    # Field Inspector user (only has roads:read, lacks roads:create)
    insp_token = await get_auth_token(async_client, email="inspector@example.com", password="InspectorSecret123!")
    headers = {"Authorization": f"Bearer {insp_token}", "X-Organization-ID": str(ORG_1_ID)}

    # Inspector attempting to create road -> 403 FORBIDDEN
    resp = await async_client.post(
        "/api/v1/roads",
        json={"name": "Unauthorized Road"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
