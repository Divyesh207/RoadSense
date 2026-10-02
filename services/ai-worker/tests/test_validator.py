from pathlib import Path

import cv2
import numpy as np
import pytest

from preprocessing.validator import (
    MediaValidationError,
    validate_media_file,
)


@pytest.fixture
def sample_image_path(tmp_path: Path) -> Path:
    img_path = tmp_path / "valid_road.jpg"
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw gray road
    img[:] = (100, 100, 100)
    cv2.imwrite(str(img_path), img)
    return img_path


@pytest.fixture
def sample_video_path(tmp_path: Path) -> Path:
    vid_path = tmp_path / "valid_road.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 10.0, (320, 240))
    for i in range(15):
        frame = np.full((240, 320, 3), 50 + i * 5, dtype=np.uint8)
        out.write(frame)
    out.release()
    return vid_path


def test_validate_valid_image(sample_image_path: Path):
    result = validate_media_file(sample_image_path, expected_type="IMAGE")
    assert result.is_valid is True
    assert result.media_type == "IMAGE"
    assert result.mime_type == "image/jpeg"
    assert result.width_px == 640
    assert result.height_px == 480
    assert result.file_size_bytes > 0


def test_validate_valid_video(sample_video_path: Path):
    result = validate_media_file(sample_video_path, expected_type="VIDEO")
    assert result.is_valid is True
    assert result.media_type == "VIDEO"
    assert result.mime_type == "video/mp4"
    assert result.width_px == 320
    assert result.height_px == 240
    assert result.frame_count is not None and result.frame_count > 0


def test_validate_file_not_found(tmp_path: Path):
    non_existent = tmp_path / "missing.jpg"
    with pytest.raises(MediaValidationError) as exc:
        validate_media_file(non_existent)
    assert exc.value.code == "FILE_NOT_FOUND"


def test_validate_empty_file(tmp_path: Path):
    empty_file = tmp_path / "empty.jpg"
    empty_file.touch()
    with pytest.raises(MediaValidationError) as exc:
        validate_media_file(empty_file)
    assert exc.value.code == "EMPTY_FILE"


def test_validate_unsupported_format(tmp_path: Path):
    unsupported = tmp_path / "document.pdf"
    unsupported.write_text("dummy")
    with pytest.raises(MediaValidationError) as exc:
        validate_media_file(unsupported)
    assert exc.value.code == "UNSUPPORTED_FORMAT"


def test_validate_media_type_mismatch(sample_image_path: Path):
    with pytest.raises(MediaValidationError) as exc:
        validate_media_file(sample_image_path, expected_type="VIDEO")
    assert exc.value.code == "MEDIA_TYPE_MISMATCH"


def test_validate_corrupt_image(tmp_path: Path):
    corrupt = tmp_path / "broken.jpg"
    corrupt.write_bytes(b"not an image file content")
    with pytest.raises(MediaValidationError) as exc:
        validate_media_file(corrupt)
    assert exc.value.code == "CORRUPT_IMAGE"
