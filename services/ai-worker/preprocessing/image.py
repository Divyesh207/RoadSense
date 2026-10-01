from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass
class PreprocessedImage:
    original_image: np.ndarray  # HxWxC BGR
    processed_tensor: np.ndarray  # 1xCxHxW float32 normalized (0-1) RGB
    orig_height: int
    orig_width: int
    target_height: int
    target_width: int
    scale: float
    pad_w: int
    pad_h: int
    quality_metrics: dict[str, Any]


def assess_image_quality(image: np.ndarray) -> dict[str, Any]:
    """Calculate blur (Laplacian variance) and brightness metrics."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    mean_brightness = float(np.mean(gray))

    is_blurry = laplacian_var < 80.0
    is_dark = mean_brightness < 40.0
    is_overexposed = mean_brightness > 220.0

    return {
        "blur_score": laplacian_var,
        "is_blurry": is_blurry,
        "mean_brightness": mean_brightness,
        "is_dark": is_dark,
        "is_overexposed": is_overexposed,
    }


def preprocess_image(
    image_or_path: np.ndarray | str,
    target_size: tuple[int, int] = (640, 640),
) -> PreprocessedImage:
    """
    Decodes, assesses quality, resizes with letterbox padding, converts BGR to RGB,
    and returns a normalized tensor ready for model inference.
    """
    if isinstance(image_or_path, str):
        img = cv2.imread(image_or_path)
        if img is None:
            raise ValueError(f"Failed to read image from path: {image_or_path}")
    else:
        img = image_or_path.copy()

    orig_h, orig_w = img.shape[:2]
    quality = assess_image_quality(img)

    target_w, target_h = target_size
    # Letterbox resize maintaining aspect ratio
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    pad_w = (target_w - new_w) // 2
    pad_h = (target_h - new_h) // 2

    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    canvas[pad_h : pad_h + new_h, pad_w : pad_w + new_w] = resized

    # BGR to RGB
    rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)

    # Normalize to 0.0 - 1.0 float32, NCHW format
    normalized = rgb.astype(np.float32) / 255.0
    tensor = np.transpose(normalized, (2, 0, 1))  # CHW
    tensor = np.expand_dims(tensor, axis=0)  # 1xCxHxW

    return PreprocessedImage(
        original_image=img,
        processed_tensor=tensor,
        orig_height=orig_h,
        orig_width=orig_w,
        target_height=target_h,
        target_width=target_w,
        scale=scale,
        pad_w=pad_w,
        pad_h=pad_h,
        quality_metrics=quality,
    )
