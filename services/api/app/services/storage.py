"""
Object storage for inspection media, repair evidence and report artifacts.

Two backends implement the same signed-URL contract:

- SupabaseStorage: Supabase Storage REST API using the service-role key. The
  key stays server-side; clients only ever receive short-lived signed URLs.
- LocalStorage: files under LOCAL_STORAGE_ROOT, uploaded through the API's own
  HMAC-signed PUT endpoint (/storage/local/...). Intended for local development
  and demos only; refused when APP_ENV=production.

Selection (STORAGE_BACKEND): "supabase", "local", or "auto" (default) which
uses Supabase when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are configured,
else local storage outside production.
"""

import hashlib
import hmac
import tempfile
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote, urlencode

import httpx
from fastapi import HTTPException

from app.core.config import settings

PLACEHOLDER_MARKERS = ("your-supabase-project", "replace-with")


class StorageError(RuntimeError):
    """Storage operation failed (network, provider error, missing object)."""


class StorageNotConfiguredError(StorageError):
    """No usable storage backend is configured for this environment."""


class StorageObjectNotFoundError(StorageError):
    """The requested object does not exist."""


class UploadTooLargeError(StorageError):
    """Upload body exceeded the configured size limit."""


class InvalidObjectKeyError(StorageError):
    """Unknown bucket or an object path that could escape its prefix."""


@dataclass
class SignedUpload:
    upload_url: str
    bucket: str
    path: str
    expires_in: int
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)


def allowed_buckets() -> set[str]:
    return {
        settings.SUPABASE_STORAGE_BUCKET_INSPECTION_MEDIA,
        settings.SUPABASE_STORAGE_BUCKET_REPAIR_EVIDENCE,
        settings.SUPABASE_STORAGE_BUCKET_REPORTS,
        settings.SUPABASE_STORAGE_BUCKET_MODEL_ARTIFACTS,
    }


def validate_object_key(bucket: str, path: str) -> str:
    """Rejects unknown buckets and keys that could escape their prefix."""
    if bucket not in allowed_buckets():
        raise InvalidObjectKeyError(f"Unknown storage bucket '{bucket}'.")
    if not path or path.startswith("/") or "\\" in path or "\x00" in path:
        raise InvalidObjectKeyError("Invalid storage path.")
    parts = PurePosixPath(path).parts
    if any(p in ("..", ".", "") for p in parts):
        raise InvalidObjectKeyError("Invalid storage path.")
    return path


def safe_filename(filename: str) -> str:
    name = PurePosixPath(filename.replace("\\", "/")).name
    cleaned = "".join(c if c.isalnum() or c in "._-" else "_" for c in name).strip("._")
    return cleaned[:120] or "upload"


class StorageBackend(Protocol):
    name: str

    def create_signed_upload(self, bucket: str, path: str, content_type: str | None = None) -> SignedUpload: ...

    def create_signed_download_url(self, bucket: str, path: str, expires_in: int) -> str: ...

    def fetch_to_local_path(self, bucket: str, path: str) -> Path: ...

    def put_object(self, bucket: str, path: str, data: bytes, content_type: str) -> None: ...


def _is_configured(value: str) -> bool:
    return bool(value) and not any(marker in value for marker in PLACEHOLDER_MARKERS)


class SupabaseStorage:
    name = "supabase"
    # Supabase signed upload URLs have a fixed validity of two hours.
    SIGNED_UPLOAD_TTL_SECONDS = 7200

    def __init__(
        self,
        url: str,
        service_role_key: str,
        timeout: float = 15.0,
        cache_dir: Path | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        if not (_is_configured(url) and _is_configured(service_role_key)):
            raise StorageNotConfiguredError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        self.base = url.rstrip("/") + "/storage/v1"
        self._headers = {"Authorization": f"Bearer {service_role_key}", "apikey": service_role_key}
        self._timeout = timeout
        self._transport = transport
        self._cache_dir = cache_dir or Path(tempfile.gettempdir()) / "road-platform-media"

    def _client(self) -> httpx.Client:
        return httpx.Client(headers=self._headers, timeout=self._timeout, transport=self._transport)

    @staticmethod
    def _key(bucket: str, path: str) -> str:
        return f"{quote(bucket)}/{quote(validate_object_key(bucket, path))}"

    def _raise_for(self, resp: httpx.Response, action: str) -> None:
        if resp.status_code < 400:
            return
        try:
            body = resp.json()
            detail = body.get("message") or body.get("error") or resp.text
        except ValueError:
            detail = resp.text
        if resp.status_code == 404 or "not found" in str(detail).lower():
            raise StorageObjectNotFoundError(f"Supabase {action}: {detail}")
        raise StorageError(f"Supabase {action} failed ({resp.status_code}): {detail}")

    def create_signed_upload(self, bucket: str, path: str, content_type: str | None = None) -> SignedUpload:
        try:
            with self._client() as client:
                resp = client.post(f"{self.base}/object/upload/sign/{self._key(bucket, path)}")
        except httpx.HTTPError as exc:
            raise StorageError(f"Supabase signed upload request failed: {exc}") from exc
        self._raise_for(resp, "signed upload")
        signed = resp.json().get("url")
        if not signed:
            raise StorageError("Supabase signed upload response did not include a URL.")
        return SignedUpload(
            upload_url=f"{self.base}{signed}",
            bucket=bucket,
            path=path,
            expires_in=self.SIGNED_UPLOAD_TTL_SECONDS,
            headers={"Content-Type": content_type} if content_type else {},
        )

    def create_signed_download_url(self, bucket: str, path: str, expires_in: int) -> str:
        try:
            with self._client() as client:
                resp = client.post(
                    f"{self.base}/object/sign/{self._key(bucket, path)}", json={"expiresIn": int(expires_in)}
                )
        except httpx.HTTPError as exc:
            raise StorageError(f"Supabase signed download request failed: {exc}") from exc
        self._raise_for(resp, "signed download")
        signed = resp.json().get("signedURL") or resp.json().get("signedUrl")
        if not signed:
            raise StorageError("Supabase signed download response did not include a URL.")
        return f"{self.base}{signed}"

    def put_object(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        try:
            with self._client() as client:
                resp = client.post(
                    f"{self.base}/object/{self._key(bucket, path)}",
                    content=data,
                    headers={"Content-Type": content_type, "x-upsert": "true"},
                )
        except httpx.HTTPError as exc:
            raise StorageError(f"Supabase upload failed: {exc}") from exc
        self._raise_for(resp, "upload")

    def fetch_to_local_path(self, bucket: str, path: str) -> Path:
        target = self._cache_dir / bucket / validate_object_key(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        try:
            with self._client() as client, client.stream(
                "GET", f"{self.base}/object/authenticated/{self._key(bucket, path)}"
            ) as resp:
                if resp.status_code >= 400:
                    resp.read()
                    self._raise_for(resp, "download")
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_bytes():
                        fh.write(chunk)
        except httpx.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            raise StorageError(f"Supabase download failed: {exc}") from exc
        tmp.replace(target)
        return target


class LocalStorage:
    name = "local"

    def __init__(self, root: Path, public_api_base_url: str, signing_secret: str, upload_ttl: int = 900):
        self.root = root
        self.public_api_base_url = public_api_base_url.rstrip("/")
        self._secret = signing_secret.encode("utf-8")
        self.upload_ttl = upload_ttl

    def _object_path(self, bucket: str, path: str) -> Path:
        resolved = (self.root / bucket / validate_object_key(bucket, path)).resolve()
        if not resolved.is_relative_to((self.root / bucket).resolve()):
            raise InvalidObjectKeyError("Invalid storage path.")
        return resolved

    def sign(self, method: str, bucket: str, path: str, expires_at: int) -> str:
        message = f"{method}\n{bucket}\n{path}\n{expires_at}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def verify(self, method: str, bucket: str, path: str, expires_at: int, signature: str) -> bool:
        if expires_at < int(time.time()):
            return False
        return hmac.compare_digest(self.sign(method, bucket, path, expires_at), signature)

    def _signed_url(self, method: str, bucket: str, path: str, ttl: int) -> str:
        validate_object_key(bucket, path)
        expires_at = int(time.time()) + ttl
        query = urlencode({"expires": expires_at, "signature": self.sign(method, bucket, path, expires_at)})
        return f"{self.public_api_base_url}/storage/local/{quote(bucket)}/{quote(path)}?{query}"

    def create_signed_upload(self, bucket: str, path: str, content_type: str | None = None) -> SignedUpload:
        return SignedUpload(
            upload_url=self._signed_url("PUT", bucket, path, self.upload_ttl),
            bucket=bucket,
            path=path,
            expires_in=self.upload_ttl,
            headers={"Content-Type": content_type} if content_type else {},
        )

    def create_signed_download_url(self, bucket: str, path: str, expires_in: int) -> str:
        if not self._object_path(bucket, path).is_file():
            raise StorageObjectNotFoundError(f"Object {bucket}/{path} does not exist.")
        return self._signed_url("GET", bucket, path, expires_in)

    async def write_chunks(self, bucket: str, path: str, chunks: AsyncIterator[bytes], max_bytes: int) -> int:
        """Streams an upload body to disk, enforcing max_bytes; atomic on success."""
        target = self._object_path(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        written = 0
        try:
            with tmp.open("wb") as fh:
                async for chunk in chunks:
                    written += len(chunk)
                    if written > max_bytes:
                        raise UploadTooLargeError(f"Upload exceeds the {max_bytes} byte limit.")
                    fh.write(chunk)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        tmp.replace(target)
        return written

    def fetch_to_local_path(self, bucket: str, path: str) -> Path:
        target = self._object_path(bucket, path)
        if not target.is_file():
            raise StorageObjectNotFoundError(f"Object {bucket}/{path} does not exist in local storage.")
        return target

    def put_object(self, bucket: str, path: str, data: bytes, content_type: str) -> None:
        target = self._object_path(bucket, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        tmp.write_bytes(data)
        tmp.replace(target)


def get_storage_backend() -> StorageBackend:
    mode = settings.STORAGE_BACKEND.strip().lower()
    supabase_ready = _is_configured(settings.SUPABASE_URL) and _is_configured(settings.SUPABASE_SERVICE_ROLE_KEY)

    if mode == "supabase" or (mode == "auto" and supabase_ready):
        return SupabaseStorage(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            timeout=settings.STORAGE_TIMEOUT_SECONDS,
            cache_dir=Path(settings.LOCAL_STORAGE_ROOT) / ".cache",
        )
    if mode in ("local", "auto"):
        if settings.APP_ENV.lower() == "production":
            raise StorageNotConfiguredError(
                "Local storage is disabled in production; configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
            )
        return LocalStorage(
            Path(settings.LOCAL_STORAGE_ROOT),
            settings.PUBLIC_API_BASE_URL,
            settings.SECRET_KEY,
            upload_ttl=settings.SIGNED_UPLOAD_EXPIRES_SECONDS,
        )
    raise StorageNotConfiguredError(f"Unknown STORAGE_BACKEND '{settings.STORAGE_BACKEND}'.")


def storage_http_exception(exc: StorageError) -> HTTPException:
    """Maps storage failures to API errors without leaking credentials."""
    if isinstance(exc, StorageNotConfiguredError):
        return HTTPException(
            status_code=503,
            detail={"code": "STORAGE_NOT_CONFIGURED", "message": str(exc)},
        )
    if isinstance(exc, StorageObjectNotFoundError):
        return HTTPException(status_code=404, detail={"code": "OBJECT_NOT_FOUND", "message": str(exc)})
    if isinstance(exc, InvalidObjectKeyError):
        return HTTPException(status_code=422, detail={"code": "INVALID_STORAGE_PATH", "message": str(exc)})
    return HTTPException(status_code=502, detail={"code": "STORAGE_UNAVAILABLE", "message": str(exc)})
