"""Signed upload/download endpoints for the local (development) storage backend.

These routes are authorized by the HMAC signature in the URL issued by the
upload-url / download-url endpoints, like a presigned object-storage URL. They
return 404 unless the active storage backend is LocalStorage.
"""

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services.storage import (
    LocalStorage,
    StorageError,
    StorageObjectNotFoundError,
    UploadTooLargeError,
    get_storage_backend,
    safe_filename,
)

router = APIRouter()


def _local_backend() -> LocalStorage:
    try:
        backend = get_storage_backend()
    except StorageError:
        backend = None
    if not isinstance(backend, LocalStorage):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Local storage is not enabled."},
        )
    return backend


def _check_signature(backend: LocalStorage, method: str, bucket: str, path: str, expires: int, signature: str) -> None:
    if not backend.verify(method, bucket, path, expires, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "INVALID_SIGNATURE", "message": "Signed URL is invalid or expired."},
        )


@router.put("/local/{bucket}/{path:path}", summary="Upload an object to local storage via a signed URL")
async def upload_local_object(
    bucket: str,
    path: str,
    request: Request,
    expires: int = Query(...),
    signature: str = Query(..., min_length=64, max_length=64),
) -> dict:
    backend = _local_backend()
    _check_signature(backend, "PUT", bucket, path, expires, signature)
    try:
        size = await backend.write_chunks(bucket, path, request.stream(), settings.MAX_MEDIA_REQUEST_SIZE_BYTES)
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "PAYLOAD_TOO_LARGE", "message": str(exc)},
        ) from exc
    except StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UPLOAD_REJECTED", "message": str(exc)},
        ) from exc
    return {"bucket": bucket, "path": path, "size_bytes": size}


@router.get("/local/{bucket}/{path:path}", summary="Download an object from local storage via a signed URL")
async def download_local_object(
    bucket: str,
    path: str,
    expires: int = Query(...),
    signature: str = Query(..., min_length=64, max_length=64),
    download: str | None = Query(None, max_length=255, description="Serve as an attachment with this file name"),
) -> FileResponse:
    backend = _local_backend()
    _check_signature(backend, "GET", bucket, path, expires, signature)
    try:
        file_path = backend.fetch_to_local_path(bucket, path)
    except StorageObjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "OBJECT_NOT_FOUND", "message": str(exc)},
        ) from exc
    # Explicit types for generated report artifacts (OS MIME tables differ, e.g. .csv on Windows).
    media_type = {".pdf": "application/pdf", ".csv": "text/csv; charset=utf-8", ".json": "application/json"}.get(
        file_path.suffix.lower()
    )
    if download:
        # Content-Disposition: attachment; the name is reduced to a safe base name.
        return FileResponse(file_path, media_type=media_type, filename=safe_filename(download))
    return FileResponse(file_path, media_type=media_type)
