"""
SYNTHETIC before/after image pairs for automated tests of the repair-verification
pipeline. These are constructed images (procedural asphalt-like texture with a drawn
"pothole"), not photographs of real repairs. Passing tests on them shows the software
behaves as designed; it says nothing about real-world repair-verification accuracy.
"""

import cv2
import numpy as np
from verification.repair_analysis import Box

W, H = 960, 720
POTHOLE_CENTER = (480, 380)
POTHOLE_AXES = (110, 70)


def asphalt(seed: int = 7) -> np.ndarray:
    """Asphalt-like texture: multi-scale noise plus aggregate specks and lane markings."""
    rng = np.random.default_rng(seed)
    base = rng.normal(115, 18, (H, W)).astype(np.float32)
    coarse = cv2.resize(rng.normal(0, 22, (H // 24, W // 24)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    img = cv2.GaussianBlur(base, (3, 3), 0) + coarse
    for _ in range(900):  # aggregate stones give ORB stable corners
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        cv2.circle(img, (x, y), int(rng.integers(2, 6)), float(rng.choice([60, 185])), -1)
    cv2.rectangle(img, (40, 60), (70, 700), 230, -1)
    for y in range(40, H, 140):
        cv2.rectangle(img, (880, y), (905, y + 80), 230, -1)
    gray = np.clip(img, 0, 255).astype(np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def with_pothole(img: np.ndarray) -> np.ndarray:
    out = img.copy()
    cv2.ellipse(out, POTHOLE_CENTER, POTHOLE_AXES, 12, 0, 360, (22, 22, 22), -1)
    rng = np.random.default_rng(3)
    for _ in range(60):  # ragged rim
        a = rng.uniform(0, 2 * np.pi)
        x = int(POTHOLE_CENTER[0] + POTHOLE_AXES[0] * np.cos(a) * rng.uniform(0.9, 1.1))
        y = int(POTHOLE_CENTER[1] + POTHOLE_AXES[1] * np.sin(a) * rng.uniform(0.9, 1.1))
        cv2.circle(out, (x, y), int(rng.integers(4, 10)), (30, 30, 30), -1)
    return out


def with_patch(img: np.ndarray) -> np.ndarray:
    """A filled repair patch: smoother, slightly darker fresh asphalt over the pothole area."""
    out = img.copy()
    rng = np.random.default_rng(11)
    patch = np.clip(rng.normal(92, 4, out.shape[:2]), 0, 255).astype(np.uint8)
    patch = cv2.GaussianBlur(patch, (9, 9), 0)
    mask = np.zeros(out.shape[:2], np.uint8)
    cv2.ellipse(mask, POTHOLE_CENTER, (POTHOLE_AXES[0] + 22, POTHOLE_AXES[1] + 22), 12, 0, 360, 255, -1)
    out[mask > 0] = cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR)[mask > 0]
    return out


def reshoot(img: np.ndarray, shift: float = 18.0, brightness: float = 8.0) -> np.ndarray:
    """Simulate a second photo of the same spot: small perspective change and exposure shift."""
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    dst = np.float32([[shift, shift / 2], [W - shift / 3, 0], [W, H - shift], [shift / 2, H]])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return np.clip(warped.astype(np.int16) + int(brightness), 0, 255).astype(np.uint8)


def encode(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    assert ok
    return buf.tobytes()


def dark_blob_detector(image: np.ndarray) -> list[Box]:
    """Test stand-in for the deployed detector: reports large very dark regions as POTHOLE.
    Used only in automated tests; production uses the trained YOLO model."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = (gray < 45).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    boxes = []
    for c in contours:
        if cv2.contourArea(c) < 2500:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        boxes.append(Box("POTHOLE", 0.8, x / w, y / h, (x + bw) / w, (y + bh) / h))
    return boxes


class SequenceDetector:
    """Returns predetermined boxes per call (first call = BEFORE image, second = AFTER image)."""

    def __init__(self, *outputs: list[Box]):
        self.outputs = list(outputs)

    def __call__(self, image: np.ndarray) -> list[Box]:
        return self.outputs.pop(0)
