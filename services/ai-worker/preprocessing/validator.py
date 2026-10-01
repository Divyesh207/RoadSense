from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2


class MediaValidationError(Exception):
    """Raised when an inspection media item fails validation."""

    def __init__(self, message: str, code: str = "INVALID_MEDIA", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass
class ValidationResult:
    is_valid: bool
    media_type: str  # "IMAGE" or "VIDEO"
    mime_type: str
    file_size_bytes: int
    width_px: int
    height_px: int
    duration_seconds: float | None = None
    frame_count: int | None = None
    fps: float | None = None
    error_message: str | None = None


SUPPORTED_IMAGE_MIMES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
}

SUPPORTED_VIDEO_MIMES = {
    "video/mp4": [".mp4"],
}

MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB
MIN_IMAGE_DIMENSION = 32
MAX_IMAGE_DIMENSION = 8192


def validate_media_file(file_path: str | Path, expected_type: str | None = None) -> ValidationResult:
    """
    Validates file existence, format, size, readability, and dimensions.
    Raises MediaValidationError if validation fails.
    """
    path = Path(file_path)
    if not path.is_file():
        raise MediaValidationError(f"File not found: {path}", code="FILE_NOT_FOUND")

    file_size = path.stat().st_size
    if file_size == 0:
        raise MediaValidationError(f"File is empty: {path}", code="EMPTY_FILE")
    if file_size > MAX_FILE_SIZE_BYTES:
        raise MediaValidationError(
            f"File exceeds maximum size limit ({file_size} > {MAX_FILE_SIZE_BYTES})",
            code="FILE_TOO_LARGE",
        )

    suffix = path.suffix.lower()

    # Determine type by extension
    is_image = any(suffix in exts for exts in SUPPORTED_IMAGE_MIMES.values())
    is_video = any(suffix in exts for exts in SUPPORTED_VIDEO_MIMES.values())

    if not is_image and not is_video:
        raise MediaValidationError(
            f"Unsupported file extension: {suffix}. Supported: JPG, PNG, MP4.",
            code="UNSUPPORTED_FORMAT",
        )

    if expected_type and expected_type == "IMAGE" and not is_image:
        raise MediaValidationError(
            f"Expected IMAGE but got file with extension {suffix}",
            code="MEDIA_TYPE_MISMATCH",
        )
    if expected_type and expected_type == "VIDEO" and not is_video:
        raise MediaValidationError(
            f"Expected VIDEO but got file with extension {suffix}",
            code="MEDIA_TYPE_MISMATCH",
        )

    if is_image:
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        # Verify readability using OpenCV
        img = cv2.imread(str(path))
        if img is None:
            raise MediaValidationError(
                f"Image file is corrupt or unreadable: {path.name}",
                code="CORRUPT_IMAGE",
            )
        h, w = img.shape[:2]
        if w < MIN_IMAGE_DIMENSION or h < MIN_IMAGE_DIMENSION:
            raise MediaValidationError(
                f"Image dimensions too small ({w}x{h}). Minimum {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}",
                code="DIMENSIONS_TOO_SMALL",
            )
        if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
            raise MediaValidationError(
                f"Image dimensions too large ({w}x{h}). Maximum {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}",
                code="DIMENSIONS_TOO_LARGE",
            )

        return ValidationResult(
            is_valid=True,
            media_type="IMAGE",
            mime_type=mime,
            file_size_bytes=file_size,
            width_px=w,
            height_px=h,
        )

    # Video validation
    mime = "video/mp4"
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise MediaValidationError(
            f"Video file is corrupt or unreadable: {path.name}",
            code="CORRUPT_VIDEO",
        )

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = (frame_count / fps) if fps > 0 else 0.0

    ret, first_frame = cap.read()
    cap.release()

    if not ret or first_frame is None:
        raise MediaValidationError(
            f"Video has no readable frames: {path.name}",
            code="EMPTY_VIDEO_FRAMES",
        )

    return ValidationResult(
        is_valid=True,
        media_type="VIDEO",
        mime_type=mime,
        file_size_bytes=file_size,
        width_px=w,
        height_px=h,
        duration_seconds=duration,
        frame_count=frame_count,
        fps=fps,
    )
