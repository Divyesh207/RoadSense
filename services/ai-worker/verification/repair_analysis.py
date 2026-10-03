"""
Before/after repair image analysis (deterministic, local OpenCV + the deployed detector).

Pipeline:
  1. decode both images; quality checks (size, exposure, sharpness)
  2. normalise (longest side = WORK_SIDE, grayscale, CLAHE for matching)
  3. ORB features + Lowe ratio matching + RANSAC homography (AFTER -> BEFORE)
     with sanity checks on the homography and the overlap it produces
  4. run the deployed detector on both images at its configured threshold;
     BEFORE detections define the documented damage regions
  5. warp AFTER onto BEFORE and measure, inside the damage regions versus the
     rest of the overlap: SSIM, normalised absolute difference, Canny edge density
  6. decide SUCCESSFUL / SUBSTANDARD / UNRESOLVED with explicit rules

There is no learned "verification score": every number reported is a measurement,
and the outcome comes from the fixed rules in `decide`. Evidence that cannot
support a decision is UNRESOLVED.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

ALGORITHM_VERSION = "repair-cv-v1.0.1"

PARAMS: dict[str, float] = {
    "work_side_px": 1024,
    "min_side_px": 240,
    "min_mean_brightness": 25.0,
    "max_mean_brightness": 235.0,
    "min_sharpness_laplacian_var": 15.0,
    "orb_features": 4000,
    "min_keypoints": 150,
    "lowe_ratio": 0.75,
    "ransac_reproj_px": 5.0,
    "min_inliers": 25,
    "min_inlier_ratio": 0.25,
    "min_overlap_fraction": 0.5,
    "min_affine_scale": 0.5,
    "max_affine_scale": 2.0,
    "max_perspective_term": 0.002,
    "region_padding_fraction": 0.15,
    "residual_min_overlap": 0.2,
    "min_region_pixels": 400,
    "min_background_ssim": 0.35,
    "min_change_contrast": 1.5,
    "min_ssim_drop": 0.10,
}

RESULT_SUCCESSFUL = "SUCCESSFUL"
RESULT_SUBSTANDARD = "SUBSTANDARD"
RESULT_UNRESOLVED = "UNRESOLVED"


@dataclass
class Box:
    """Detection box in normalised [0, 1] image coordinates."""

    damage_type_code: str
    confidence: float
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "damage_type": self.damage_type_code,
            "confidence": round(float(self.confidence), 4),
            "bbox": [round(self.x_min, 4), round(self.y_min, 4), round(self.x_max, 4), round(self.y_max, 4)],
        }


# detect(image_bgr) -> boxes. The worker passes the deployed YOLO detector at its threshold.
DetectFn = Callable[[np.ndarray], list[Box]]


@dataclass
class RepairAnalysis:
    result: str
    reason_code: str
    reasons: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    before_detections: list[dict[str, Any]] = field(default_factory=list)
    after_detections: list[dict[str, Any]] = field(default_factory=list)
    residual_detections: list[dict[str, Any]] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)

    def findings(self) -> dict[str, Any]:
        return {
            "check_type": "AUTOMATED_IMAGE_ANALYSIS",
            "algorithm_version": ALGORITHM_VERSION,
            "result": self.result,
            "reason_code": self.reason_code,
            "reasons": self.reasons,
            "checks": self.checks,
            "before_detection_count": len(self.before_detections),
            "after_detection_count": len(self.after_detections),
            "residual_detection_count": len(self.residual_detections),
            "before_detections": self.before_detections,
            "after_detections": self.after_detections,
            "residual_detections": self.residual_detections,
            "image_comparison_performed": True,
            "human_review_required": True,
            "parameters": PARAMS,
        }


def _unresolved(code: str, reason: str, checks: dict[str, Any], metrics: dict[str, Any] | None = None) -> RepairAnalysis:
    return RepairAnalysis(RESULT_UNRESOLVED, code, [reason], metrics or {}, checks=checks)


def decode_image(data: bytes) -> np.ndarray | None:
    if not data:
        return None
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img if img is not None and img.size > 0 else None


def image_quality(img: np.ndarray) -> dict[str, Any]:
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Sharpness is measured at native resolution, downscaled only: upscaling a small
    # photo would blur it and understate its sharpness.
    scale = min(1.0, PARAMS["work_side_px"] / max(h, w))
    small = cv2.resize(gray, (max(1, round(w * scale)), max(1, round(h * scale))), interpolation=cv2.INTER_AREA)
    brightness = float(gray.mean())
    sharpness = float(cv2.Laplacian(small, cv2.CV_64F).var())
    problems = []
    if min(h, w) < PARAMS["min_side_px"]:
        problems.append("TOO_SMALL")
    if not PARAMS["min_mean_brightness"] <= brightness <= PARAMS["max_mean_brightness"]:
        problems.append("BAD_EXPOSURE")
    if sharpness < PARAMS["min_sharpness_laplacian_var"]:
        problems.append("TOO_BLURRY")
    return {
        "width_px": int(w),
        "height_px": int(h),
        "mean_brightness": round(brightness, 2),
        "sharpness_laplacian_var": round(sharpness, 2),
        "problems": problems,
        "ok": not problems,
    }


def normalise(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    scale = PARAMS["work_side_px"] / max(h, w)
    resized = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)


def align(before_gray: np.ndarray, after_gray: np.ndarray) -> dict[str, Any]:
    """ORB + ratio test + RANSAC homography mapping AFTER onto BEFORE, with sanity checks."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    orb = cv2.ORB_create(nfeatures=int(PARAMS["orb_features"]))
    kp_b, des_b = orb.detectAndCompute(clahe.apply(before_gray), None)
    kp_a, des_a = orb.detectAndCompute(clahe.apply(after_gray), None)
    out: dict[str, Any] = {
        "keypoints_before": len(kp_b),
        "keypoints_after": len(kp_a),
        "good_matches": 0,
        "inliers": 0,
        "inlier_ratio": 0.0,
        "overlap_fraction": 0.0,
        "homography": None,
        "aligned": False,
        "failure": None,
    }
    if len(kp_b) < PARAMS["min_keypoints"] or len(kp_a) < PARAMS["min_keypoints"] or des_b is None or des_a is None:
        out["failure"] = "INSUFFICIENT_FEATURES"
        return out

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    good = []
    for pair in matcher.knnMatch(des_a, des_b, k=2):
        if len(pair) == 2 and pair[0].distance < PARAMS["lowe_ratio"] * pair[1].distance:
            good.append(pair[0])
    out["good_matches"] = len(good)
    if len(good) < PARAMS["min_inliers"]:
        out["failure"] = "TOO_FEW_MATCHES"
        return out

    src = np.float32([kp_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, PARAMS["ransac_reproj_px"])
    if H is None or mask is None:
        out["failure"] = "HOMOGRAPHY_NOT_FOUND"
        return out
    inliers = int(mask.sum())
    ratio = inliers / len(good)
    out.update(inliers=inliers, inlier_ratio=round(ratio, 4))

    det = float(np.linalg.det(H[:2, :2]))
    scale = float(np.sqrt(abs(det)))
    persp = float(max(abs(H[2, 0]), abs(H[2, 1])))
    hb, wb = before_gray.shape[:2]
    ha, wa = after_gray.shape[:2]
    corners = cv2.perspectiveTransform(np.float32([[0, 0], [wa, 0], [wa, ha], [0, ha]]).reshape(-1, 1, 2), H)
    canvas = np.zeros((hb, wb), np.uint8)
    cv2.fillConvexPoly(canvas, np.int32(corners.reshape(-1, 2)), 1)
    overlap = float(canvas.mean())
    out.update(overlap_fraction=round(overlap, 4), affine_scale=round(scale, 4), perspective_term=round(persp, 6))

    if inliers < PARAMS["min_inliers"] or ratio < PARAMS["min_inlier_ratio"]:
        out["failure"] = "TOO_FEW_INLIERS"
    elif det <= 0 or not PARAMS["min_affine_scale"] <= scale <= PARAMS["max_affine_scale"]:
        out["failure"] = "DEGENERATE_HOMOGRAPHY"
    elif persp > PARAMS["max_perspective_term"]:
        out["failure"] = "EXCESSIVE_PERSPECTIVE"
    elif overlap < PARAMS["min_overlap_fraction"]:
        out["failure"] = "INSUFFICIENT_OVERLAP"
    else:
        out["aligned"] = True
        out["homography"] = [[round(float(v), 8) for v in row] for row in H]
    return out


def _ssim_map(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Gaussian-window SSIM (Wang et al. 2004) on 8-bit grayscale images."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    blur = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    mu_a, mu_b = blur(a), blur(b)
    var_a = blur(a * a) - mu_a**2
    var_b = blur(b * b) - mu_b**2
    cov = blur(a * b) - mu_a * mu_b
    return ((2 * mu_a * mu_b + c1) * (2 * cov + c2)) / ((mu_a**2 + mu_b**2 + c1) * (var_a + var_b + c2))


def _standardise(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    vals = img[mask].astype(np.float64)
    std = vals.std() or 1.0
    return (img.astype(np.float64) - vals.mean()) / std


def _box_px(box: Box, w: int, h: int, pad: float = 0.0) -> tuple[int, int, int, int]:
    bw, bh = (box.x_max - box.x_min) * w, (box.y_max - box.y_min) * h
    x0 = max(0, int((box.x_min * w) - pad * bw))
    y0 = max(0, int((box.y_min * h) - pad * bh))
    x1 = min(w, int(np.ceil(box.x_max * w + pad * bw)))
    y1 = min(h, int(np.ceil(box.y_max * h + pad * bh)))
    return x0, y0, x1, y1


def _warp_box(box: Box, H: np.ndarray, wa: int, ha: int, wb: int, hb: int) -> Box:
    pts = np.float32([
        [box.x_min * wa, box.y_min * ha], [box.x_max * wa, box.y_min * ha],
        [box.x_max * wa, box.y_max * ha], [box.x_min * wa, box.y_max * ha],
    ]).reshape(-1, 1, 2)
    p = cv2.perspectiveTransform(pts, H).reshape(-1, 2)
    return Box(
        box.damage_type_code, box.confidence,
        float(np.clip(p[:, 0].min() / wb, 0, 1)), float(np.clip(p[:, 1].min() / hb, 0, 1)),
        float(np.clip(p[:, 0].max() / wb, 0, 1)), float(np.clip(p[:, 1].max() / hb, 0, 1)),
    )


def _overlap_of(a: Box, b: Box) -> float:
    """Intersection area as a fraction of the smaller box."""
    ix = max(0.0, min(a.x_max, b.x_max) - max(a.x_min, b.x_min))
    iy = max(0.0, min(a.y_max, b.y_max) - max(a.y_min, b.y_min))
    smaller = min((a.x_max - a.x_min) * (a.y_max - a.y_min), (b.x_max - b.x_min) * (b.y_max - b.y_min))
    return (ix * iy) / smaller if smaller > 0 else 0.0


def region_metrics(before_gray: np.ndarray, warped_after: np.ndarray, valid: np.ndarray, regions: list[Box]) -> dict[str, Any]:
    hb, wb = before_gray.shape[:2]
    region_mask = np.zeros((hb, wb), bool)
    for box in regions:
        x0, y0, x1, y1 = _box_px(box, wb, hb, PARAMS["region_padding_fraction"])
        region_mask[y0:y1, x0:x1] = True
    inside = region_mask & valid
    outside = (~region_mask) & valid
    if inside.sum() < PARAMS["min_region_pixels"] or outside.sum() < PARAMS["min_region_pixels"]:
        return {"region_pixels": int(inside.sum()), "background_pixels": int(outside.sum()), "measurable": False}

    ssim = _ssim_map(before_gray, warped_after)
    diff = np.abs(_standardise(before_gray, valid) - _standardise(warped_after, valid))
    edges_b = cv2.Canny(before_gray, 60, 160) > 0
    edges_a = cv2.Canny(warped_after, 60, 160) > 0
    region_diff = float(diff[inside].mean())
    background_diff = float(diff[outside].mean())
    eb, ea = float(edges_b[inside].mean()), float(edges_a[inside].mean())
    return {
        "measurable": True,
        "region_pixels": int(inside.sum()),
        "background_pixels": int(outside.sum()),
        "region_ssim": round(float(ssim[inside].mean()), 4),
        "background_ssim": round(float(ssim[outside].mean()), 4),
        "region_mean_abs_diff_z": round(region_diff, 4),
        "background_mean_abs_diff_z": round(background_diff, 4),
        "change_contrast": round(region_diff / max(background_diff, 1e-6), 4),
        "region_edge_density_before": round(eb, 4),
        "region_edge_density_after": round(ea, 4),
        "region_edge_density_ratio": round(ea / eb, 4) if eb > 0 else None,
    }


def decide(
    before_boxes: list[Box], residual: list[Box], metrics: dict[str, Any]
) -> tuple[str, str, list[str]]:
    if residual:
        types = sorted({b.damage_type_code for b in residual})
        return (
            RESULT_SUBSTANDARD, "RESIDUAL_DAMAGE_DETECTED",
            [(f"The detector still finds {len(residual)} damage region(s) ({', '.join(types)}) "
             "overlapping the documented damage in the AFTER image.")],
        )
    if not before_boxes:
        return (
            RESULT_UNRESOLVED, "BEFORE_DAMAGE_NOT_DETECTED",
            ["The detector found no damage in the BEFORE image, so there is no image region to check the repair against."],
        )
    if not metrics.get("measurable"):
        return (
            RESULT_UNRESOLVED, "REGION_NOT_MEASURABLE",
            ["The documented damage region is not sufficiently covered by the aligned AFTER image."],
        )
    if metrics["background_ssim"] < PARAMS["min_background_ssim"]:
        return (
            RESULT_UNRESOLVED, "SCENE_TOO_DIFFERENT",
            [f"Unchanged surroundings differ too much (SSIM {metrics['background_ssim']:.2f}) to attribute changes to the repair."],
        )
    changed = (
        metrics["change_contrast"] >= PARAMS["min_change_contrast"]
        and metrics["region_ssim"] <= metrics["background_ssim"] - PARAMS["min_ssim_drop"]
    )
    if not changed:
        return (
            RESULT_UNRESOLVED, "REGION_UNCHANGED",
            [("No damage is detected after repair, but the damage region did not change measurably relative to its "
             "surroundings; a detector miss cannot be ruled out.")],
        )
    return (
        RESULT_SUCCESSFUL, "DAMAGE_REGION_REPAIRED",
        [(f"The documented damage region changed (change contrast {metrics['change_contrast']:.2f}, region SSIM "
         f"{metrics['region_ssim']:.2f} vs surroundings {metrics['background_ssim']:.2f}) and no damage is detected there "
         "in the AFTER image.")],
    )


def analyze_repair_pair(before_bytes: bytes, after_bytes: bytes, detect: DetectFn) -> RepairAnalysis:
    checks: dict[str, Any] = {}
    before = decode_image(before_bytes)
    after = decode_image(after_bytes)
    checks["decoded"] = {"before": before is not None, "after": after is not None}
    if before is None or after is None:
        side = "BEFORE" if before is None else "AFTER"
        return _unresolved("IMAGE_DECODE_FAILED", f"The {side} image could not be decoded (corrupted or not an image).", checks)

    q_before, q_after = image_quality(before), image_quality(after)
    checks["quality"] = {"before": q_before, "after": q_after}
    if not (q_before["ok"] and q_after["ok"]):
        probs = [f"BEFORE: {p}" for p in q_before["problems"]] + [f"AFTER: {p}" for p in q_after["problems"]]
        return _unresolved("POOR_IMAGE_QUALITY", "Image quality is insufficient: " + ", ".join(probs) + ".", checks)

    before_gray, after_gray = normalise(before), normalise(after)
    alignment = align(before_gray, after_gray)
    checks["alignment"] = {k: v for k, v in alignment.items() if k != "homography"}
    metrics: dict[str, Any] = {"alignment": checks["alignment"]}

    # Detection runs regardless of alignment so the counts are always reported.
    before_boxes = detect(before)
    after_boxes = detect(after)
    if not alignment["aligned"]:
        code = "INSUFFICIENT_FEATURES" if alignment["failure"] == "INSUFFICIENT_FEATURES" else "ALIGNMENT_FAILED"
        analysis = _unresolved(
            code,
            f"BEFORE and AFTER images could not be reliably aligned ({alignment['failure']}); "
            "they may not show the same location.",
            checks, metrics,
        )
        analysis.before_detections = [b.as_dict() for b in before_boxes]
        analysis.after_detections = [b.as_dict() for b in after_boxes]
        return analysis

    H = np.array(alignment["homography"], dtype=np.float64)
    hb, wb = before_gray.shape[:2]
    ha, wa = after_gray.shape[:2]
    warped = cv2.warpPerspective(after_gray, H, (wb, hb), flags=cv2.INTER_LINEAR, borderValue=0)
    valid = cv2.warpPerspective(np.full((ha, wa), 255, np.uint8), H, (wb, hb), flags=cv2.INTER_NEAREST) > 0
    valid = cv2.erode(valid.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0

    after_in_before = [_warp_box(b, H, wa, ha, wb, hb) for b in after_boxes]
    residual = [
        a for a in after_in_before
        if any(_overlap_of(a, b) >= PARAMS["residual_min_overlap"] for b in before_boxes)
    ]
    metrics["region"] = region_metrics(before_gray, warped, valid, before_boxes) if before_boxes else {"measurable": False}
    result, code, reasons = decide(before_boxes, residual, metrics["region"])
    return RepairAnalysis(
        result, code, reasons, metrics,
        before_detections=[b.as_dict() for b in before_boxes],
        after_detections=[b.as_dict() for b in after_in_before],
        residual_detections=[b.as_dict() for b in residual],
        checks=checks,
    )
