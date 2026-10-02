from pathlib import Path

import cv2
import numpy as np
import pytest

from preprocessing.image import assess_image_quality, preprocess_image
from preprocessing.video import sample_video_frames


@pytest.fixture
def test_image(tmp_path: Path) -> Path:
    p = tmp_path / "img_test.jpg"
    arr = np.zeros((300, 400, 3), dtype=np.uint8)
    # Add high contrast patterns
    cv2.circle(arr, (200, 150), 50, (255, 255, 255), -1)
    cv2.imwrite(str(p), arr)
    return p


@pytest.fixture
def test_video(tmp_path: Path) -> Path:
    vid_path = tmp_path / "vid_test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(vid_path), fourcc, 10.0, (160, 120))
    for i in range(20):
        frame = np.full((120, 160, 3), i * 10, dtype=np.uint8)
        out.write(frame)
    out.release()
    return vid_path


def test_assess_image_quality():
    # Crisp image
    crisp = np.zeros((100, 100, 3), dtype=np.uint8)
    crisp[::2, :] = 255
    q_crisp = assess_image_quality(crisp)
    assert q_crisp["blur_score"] > 80.0
    assert q_crisp["is_blurry"] is False

    # Uniform/blurred image
    blurry = np.full((100, 100, 3), 128, dtype=np.uint8)
    q_blur = assess_image_quality(blurry)
    assert q_blur["blur_score"] < 10.0
    assert q_blur["is_blurry"] is True


def test_preprocess_image(test_image: Path):
    prep = preprocess_image(str(test_image), target_size=(640, 640))
    assert prep.orig_height == 300
    assert prep.orig_width == 400
    assert prep.target_height == 640
    assert prep.target_width == 640

    # Output tensor shape must be 1 x 3 x 640 x 640
    assert prep.processed_tensor.shape == (1, 3, 640, 640)
    assert prep.processed_tensor.dtype == np.float32
    assert prep.processed_tensor.min() >= 0.0
    assert prep.processed_tensor.max() <= 1.0


def test_sample_video_frames(test_video: Path):
    frames = list(sample_video_frames(test_video, sample_fps=2.0))
    assert len(frames) > 0
    first = frames[0]
    assert first.frame_number == 0
    assert first.timestamp_ms == 0
    assert first.image.shape == (120, 160, 3)
