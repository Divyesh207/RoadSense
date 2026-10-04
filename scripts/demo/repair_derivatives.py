"""
DEMO / SYNTHETIC "after repair" images for the faculty demo dataset.

Each function takes a genuine BEFORE photograph (RDD2022) and returns an EDITED COPY that
imitates a later photo of the same spot. These are constructed images, not photographs of
real repairs. Every output carries a burned-in caption saying so.

    repaired(...)   the detected damage regions are filled and covered with a patch
    partial(...)    only part of each damage region is patched; the rest is left as it was
    unchanged(...)  nothing is repaired; only the "second photo" camera/exposure change

The repair-verification outcome is never set here. It is whatever the real pipeline
decides when it compares the BEFORE photo with one of these images.
"""

from __future__ import annotations

import cv2
import numpy as np

Box = tuple[float, float, float, float]  # x_min, y_min, x_max, y_max, normalised [0, 1]

CAPTION = "DEMO / SYNTHETIC after-repair image - edited copy of the BEFORE photo, not a real repair"


def _region_mask(shape: tuple[int, int], boxes: list[Box], pad: float, part: float = 1.0) -> np.ndarray:
    """Filled, soft-cornered mask over the boxes. `part` < 1 keeps only the left share of each box."""
    h, w = shape
    mask = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in boxes:
        bw, bh = (x1 - x0) * w, (y1 - y0) * h
        px0, py0 = int(x0 * w - pad * bw), int(y0 * h - pad * bh)
        px1, py1 = int(x1 * w + pad * bw), int(y1 * h + pad * bh)
        px1 = int(px0 + (px1 - px0) * part)
        cv2.rectangle(mask, (max(0, px0), max(0, py0)), (min(w - 1, px1), min(h - 1, py1)), 255, -1)
    return mask


def _patch(img: np.ndarray, mask: np.ndarray, seed: int) -> np.ndarray:
    """Remove what is inside the mask (inpainting) and lay a darker, even 'fresh asphalt' patch over it."""
    filled = cv2.inpaint(img, mask, 7, cv2.INPAINT_TELEA)
    rng = np.random.default_rng(seed)
    tone = float(np.median(cv2.cvtColor(filled, cv2.COLOR_BGR2GRAY)[mask > 0])) * 0.62
    fresh = np.clip(rng.normal(tone, 4.0, img.shape[:2]), 0, 255).astype(np.uint8)
    fresh = cv2.cvtColor(cv2.GaussianBlur(fresh, (5, 5), 0), cv2.COLOR_GRAY2BGR)
    alpha = cv2.GaussianBlur(mask.astype(np.float32) / 255.0, (0, 0), 3.0)[..., None] * 0.80
    return np.clip(filled * (1 - alpha) + fresh * alpha, 0, 255).astype(np.uint8)


def _reshoot(img: np.ndarray, seed: int) -> np.ndarray:
    """A second photo of the same spot: slightly shifted/rotated camera and different exposure."""
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), float(rng.uniform(-0.8, 0.8)), float(rng.uniform(0.985, 1.015)))
    M[:, 2] += rng.uniform(-6, 6, 2)
    out = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    out = np.clip(out.astype(np.float32) * float(rng.uniform(0.95, 1.05)) + float(rng.uniform(-5, 5)), 0, 255)
    return out.astype(np.uint8)


def _caption(img: np.ndarray) -> np.ndarray:
    out = img.copy()
    h, w = out.shape[:2]
    cv2.rectangle(out, (0, h - 22), (w, h), (16, 16, 16), -1)
    cv2.putText(out, CAPTION, (6, h - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (235, 235, 235), 1, cv2.LINE_AA)
    return out


def decode(data: bytes) -> np.ndarray:
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not an image")
    return img


def encode(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buf.tobytes()


def repaired(before: bytes, boxes: list[Box], seed: int = 1) -> bytes:
    img = decode(before)
    return encode(_caption(_reshoot(_patch(img, _region_mask(img.shape[:2], boxes, 0.18), seed), seed)))


def partial(before: bytes, boxes: list[Box], seed: int = 1, part: float = 0.4) -> bytes:
    img = decode(before)
    return encode(_caption(_reshoot(_patch(img, _region_mask(img.shape[:2], boxes, 0.10, part), seed), seed)))


def unchanged(before: bytes, seed: int = 1) -> bytes:
    return encode(_caption(_reshoot(decode(before), seed)))
