"""Object storage: local signed-URL backend, Supabase REST client, endpoint wiring."""

import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.core.config import settings
from app.services.storage import (
    InvalidObjectKeyError,
    LocalStorage,
    StorageError,
    StorageNotConfiguredError,
    StorageObjectNotFoundError,
    SupabaseStorage,
    get_storage_backend,
    validate_object_key,
)
from tests.conftest import ORG_1_ID
from tests.test_inspections import get_token

SERVICE_KEY = "service-role-secret-for-tests"
SUPABASE_URL = "https://abc123.supabase.co"


async def _inspector_headers(async_client):
    token = await get_token(async_client)
    return {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}


async def _new_inspection(async_client, headers) -> str:
    return (await async_client.post("/api/v1/inspections", json={"notes": "storage"}, headers=headers)).json()["data"]["id"]


def _relative(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.path}?{parsed.query}"


# --- Local backend -----------------------------------------------------------


@pytest.mark.asyncio
async def test_local_signed_upload_round_trip(async_client, isolated_local_storage):
    headers = await _inspector_headers(async_client)
    insp_id = await _new_inspection(async_client, headers)

    url_resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/upload-url",
        json={"filename": "../../etc/road photo.jpg", "content_type": "image/jpeg", "size_bytes": 5},
        headers=headers,
    )
    assert url_resp.status_code == 200
    data = url_resp.json()["data"]
    assert data["upload_method"] == "PUT"
    assert data["upload_headers"] == {"Content-Type": "image/jpeg"}
    assert data["storage_path"].startswith(f"inspections/{insp_id}/")
    assert data["storage_path"].endswith("_road_photo.jpg")  # directory components stripped

    put = await async_client.put(_relative(data["upload_url"]), content=b"hello", headers=data["upload_headers"])
    assert put.status_code == 200
    stored = isolated_local_storage / data["storage_bucket"] / data["storage_path"]
    assert stored.read_bytes() == b"hello"

    complete = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/complete",
        json={
            "storage_path": data["storage_path"],
            "storage_bucket": data["storage_bucket"],
            "media_type": "IMAGE",
            "mime_type": "image/jpeg",
            "size_bytes": 5,
        },
        headers=headers,
    )
    assert complete.status_code == 201


@pytest.mark.asyncio
async def test_local_upload_rejects_tampered_and_expired_signatures(async_client):
    backend = get_storage_backend()
    url = backend.create_signed_upload("inspection-media", "inspections/x/a.jpg").upload_url
    query = parse_qs(urlparse(url).query)

    tampered = url.replace("inspections/x/a.jpg", "inspections/y/a.jpg")
    assert (await async_client.put(_relative(tampered), content=b"x")).status_code == 403

    expired_at = int(time.time()) - 5
    expired_sig = backend.sign("PUT", "inspection-media", "inspections/x/a.jpg", expired_at)
    expired = _relative(url).split("?")[0] + f"?expires={expired_at}&signature={expired_sig}"
    assert (await async_client.put(expired, content=b"x")).status_code == 403

    # A GET signature cannot be used to upload.
    get_sig = backend.sign("GET", "inspection-media", "inspections/x/a.jpg", int(query["expires"][0]))
    wrong_method = _relative(url).split("?")[0] + f"?expires={query['expires'][0]}&signature={get_sig}"
    assert (await async_client.put(wrong_method, content=b"x")).status_code == 403


@pytest.mark.asyncio
async def test_local_upload_enforces_size_limit(async_client, monkeypatch, isolated_local_storage):
    monkeypatch.setattr(settings, "MAX_MEDIA_REQUEST_SIZE_BYTES", 8)
    url = get_storage_backend().create_signed_upload("inspection-media", "inspections/x/big.jpg").upload_url

    # Declared Content-Length is rejected up front by the request-size middleware.
    declared = await async_client.put(_relative(url), content=b"0123456789")
    assert declared.status_code == 413

    # Chunked bodies (no Content-Length) are cut off by the endpoint while streaming.
    async def chunks():
        for _ in range(5):
            yield b"0123"

    streamed = await async_client.put(_relative(url), content=chunks())
    assert streamed.status_code == 413
    assert streamed.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert not (isolated_local_storage / "inspection-media" / "inspections/x/big.jpg").exists()


@pytest.mark.parametrize(
    ("bucket", "path"),
    [
        ("inspection-media", "../secrets.txt"),
        ("inspection-media", "inspections/../../x"),
        ("inspection-media", "/abs/path"),
        ("inspection-media", "a\\b"),
        ("not-a-bucket", "inspections/a.jpg"),
    ],
)
def test_object_key_validation_rejects_escapes(bucket, path):
    with pytest.raises(InvalidObjectKeyError):
        validate_object_key(bucket, path)


@pytest.mark.asyncio
async def test_complete_rejects_paths_not_issued_for_the_inspection(async_client):
    headers = await _inspector_headers(async_client)
    insp_id = await _new_inspection(async_client, headers)
    other_id = await _new_inspection(async_client, headers)

    for bucket, path in [
        ("inspection-media", f"inspections/{other_id}/a.jpg"),
        ("repair-evidence", f"inspections/{insp_id}/a.jpg"),
        ("inspection-media", f"inspections/{insp_id}/../{other_id}/a.jpg"),
    ]:
        resp = await async_client.post(
            f"/api/v1/inspections/{insp_id}/media/complete",
            json={"storage_path": path, "storage_bucket": bucket, "media_type": "IMAGE", "mime_type": "image/jpeg", "size_bytes": 1},
            headers=headers,
        )
        assert resp.status_code == 422, path
        assert resp.json()["error"]["code"] == "INVALID_STORAGE_PATH"


@pytest.mark.asyncio
async def test_production_without_supabase_reports_storage_not_configured(async_client, monkeypatch):
    headers = await _inspector_headers(async_client)
    insp_id = await _new_inspection(async_client, headers)
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "auto")
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "SUPABASE_URL", "")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")

    resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/upload-url",
        json={"filename": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1},
        headers=headers,
    )

    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "STORAGE_NOT_CONFIGURED"


def test_placeholder_supabase_values_are_not_treated_as_configured(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://your-supabase-project.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "replace-with-service-role-key")
    with pytest.raises(StorageNotConfiguredError):
        get_storage_backend()


# --- Supabase backend (HTTP mocked; no live project is contacted) --------------


class FakeSupabase:
    """Minimal stand-in for the Supabase Storage REST API."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.objects: dict[str, bytes] = {"inspection-media/inspections/i1/a.jpg": b"jpeg-bytes"}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/storage/v1")
        assert request.headers["Authorization"] == f"Bearer {SERVICE_KEY}"
        assert request.headers["apikey"] == SERVICE_KEY
        if path.startswith("/object/upload/sign/"):
            key = path.removeprefix("/object/upload/sign/")
            return httpx.Response(200, json={"url": f"/object/upload/sign/{key}?token=signed-upload-token"})
        if path.startswith("/object/sign/"):
            key = path.removeprefix("/object/sign/")
            if key not in self.objects:
                return httpx.Response(400, json={"statusCode": "404", "error": "not_found", "message": "Object not found"})
            assert json.loads(request.content)["expiresIn"] == 600
            return httpx.Response(200, json={"signedURL": f"/object/sign/{key}?token=signed-download-token"})
        if path.startswith("/object/authenticated/") and request.method == "GET":
            key = path.removeprefix("/object/authenticated/")
            if key not in self.objects:
                return httpx.Response(400, json={"error": "not_found", "message": "Object not found"})
            return httpx.Response(200, content=self.objects[key])
        if path.startswith("/object/") and request.method == "POST":
            self.objects[path.removeprefix("/object/")] = request.content
            assert request.headers["x-upsert"] == "true"
            return httpx.Response(200, json={"Key": path})
        return httpx.Response(500, json={"message": "unexpected request"})


def _supabase(fake: FakeSupabase, tmp_path) -> SupabaseStorage:
    return SupabaseStorage(SUPABASE_URL, SERVICE_KEY, cache_dir=tmp_path, transport=httpx.MockTransport(fake))


def test_supabase_signed_upload_url(tmp_path):
    fake = FakeSupabase()
    signed = _supabase(fake, tmp_path).create_signed_upload("inspection-media", "inspections/i1/b.jpg", "image/jpeg")

    assert signed.upload_url == (
        f"{SUPABASE_URL}/storage/v1/object/upload/sign/inspection-media/inspections/i1/b.jpg?token=signed-upload-token"
    )
    assert signed.expires_in == 7200
    assert signed.headers == {"Content-Type": "image/jpeg"}
    assert SERVICE_KEY not in signed.upload_url
    assert fake.requests[0].method == "POST"


def test_supabase_download_fetch_and_put(tmp_path):
    fake = FakeSupabase()
    storage = _supabase(fake, tmp_path)

    url = storage.create_signed_download_url("inspection-media", "inspections/i1/a.jpg", 600)
    assert url.endswith("/object/sign/inspection-media/inspections/i1/a.jpg?token=signed-download-token")

    local = storage.fetch_to_local_path("inspection-media", "inspections/i1/a.jpg")
    assert local.read_bytes() == b"jpeg-bytes"

    storage.put_object("reports", "reports/o/r.json", b"{}", "application/json")
    assert fake.objects["reports/reports/o/r.json"] == b"{}"


def test_supabase_missing_object_and_provider_errors(tmp_path):
    storage = _supabase(FakeSupabase(), tmp_path)
    with pytest.raises(StorageObjectNotFoundError):
        storage.create_signed_download_url("inspection-media", "inspections/i1/missing.jpg", 600)
    with pytest.raises(StorageObjectNotFoundError):
        storage.fetch_to_local_path("inspection-media", "inspections/i1/missing.jpg")

    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)

    broken = SupabaseStorage(SUPABASE_URL, SERVICE_KEY, cache_dir=tmp_path, transport=httpx.MockTransport(boom))
    with pytest.raises(StorageError):
        broken.create_signed_upload("inspection-media", "inspections/i1/a.jpg")


@pytest.mark.asyncio
async def test_upload_url_endpoint_uses_supabase_when_configured(async_client, monkeypatch, tmp_path):
    fake = FakeSupabase()
    monkeypatch.setattr(
        "app.api.v1.endpoints.inspections.get_storage_backend", lambda: _supabase(fake, tmp_path)
    )
    headers = await _inspector_headers(async_client)
    insp_id = await _new_inspection(async_client, headers)

    resp = await async_client.post(
        f"/api/v1/inspections/{insp_id}/media/upload-url",
        json={"filename": "a.jpg", "content_type": "image/jpeg", "size_bytes": 1},
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["upload_url"].startswith(f"{SUPABASE_URL}/storage/v1/object/upload/sign/inspection-media/inspections/{insp_id}/")
    assert data["expires_in"] == 7200
    assert SERVICE_KEY not in resp.text


# --- Reports ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_artifact_is_generated_and_downloadable(async_client):
    token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    created = await async_client.post(
        "/api/v1/reports", json={"report_type": "ROAD_HEALTH", "parameters": {"format": "PDF"}}, headers=headers
    )
    report_id = created.json()["data"]["report_id"]
    detail = (await async_client.get(f"/api/v1/reports/{report_id}", headers=headers)).json()["data"]
    assert detail["status"] == "COMPLETED"
    assert detail["parameters"]["requested_format"] == "PDF"
    assert detail["parameters"]["artifact_format"] == "PDF"

    dl = (await async_client.get(f"/api/v1/reports/{report_id}/download-url", headers=headers)).json()["data"]
    artifact = await async_client.get(_relative(dl["download_url"]))
    assert artifact.status_code == 200
    assert artifact.headers["content-type"] == "application/pdf"
    assert artifact.content.startswith(b"%PDF-1.4")
    assert b"Road Health Report" in artifact.content and b"Road Health" in artifact.content


@pytest.mark.asyncio
async def test_report_marked_failed_when_artifact_upload_fails(async_client, monkeypatch):
    class BrokenStorage(LocalStorage):
        def put_object(self, *args, **kwargs):
            raise StorageError("bucket unavailable")

    monkeypatch.setattr(
        "app.services.report_service.get_storage_backend",
        lambda: BrokenStorage(Path(settings.LOCAL_STORAGE_ROOT), "http://testserver/api/v1", "s"),
    )
    token = await get_token(async_client, email="authority@example.com", password="AuthoritySecret123!")
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(ORG_1_ID)}

    created = await async_client.post("/api/v1/reports", json={"report_type": "ROAD_HEALTH"}, headers=headers)
    assert created.json()["data"]["status"] == "FAILED"
    report_id = created.json()["data"]["report_id"]

    dl = await async_client.get(f"/api/v1/reports/{report_id}/download-url", headers=headers)
    assert dl.status_code == 409
    assert dl.json()["error"]["code"] == "REPORT_ARTIFACT_NOT_AVAILABLE"
