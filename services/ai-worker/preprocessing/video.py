from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class ExtractedFrame:
    frame_number: int
    timestamp_ms: int
    image: np.ndarray  # HxWxC BGR
    fps: float


def sample_video_frames(
    video_path: str | Path,
    sample_fps: float = 1.0,
    max_frames: int = 100,
) -> Generator[ExtractedFrame, None, None]:
    """
    Extracts frames from video at `sample_fps` (e.g. 1 frame per second).
    Yields ExtractedFrame objects with frame_number and timestamp_ms.
    """
    path = Path(video_path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    video_fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0

    # Calculate step in frames
    step = max(1, round(video_fps / sample_fps)) if sample_fps > 0 else 1

    current_frame_idx = 0
    yielded_count = 0

    try:
        while cap.isOpened() and yielded_count < max_frames:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if current_frame_idx % step == 0:
                timestamp_ms = round((current_frame_idx / video_fps) * 1000.0)
                yield ExtractedFrame(
                    frame_number=current_frame_idx,
                    timestamp_ms=timestamp_ms,
                    image=frame,
                    fps=video_fps,
                )
                yielded_count += 1

            current_frame_idx += 1
    finally:
        cap.release()
