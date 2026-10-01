from dataclasses import dataclass
from typing import Any


@dataclass
class RawDetection:
    damage_type_code: str
    confidence: float
    bbox_x_min: float
    bbox_y_min: float
    bbox_x_max: float
    bbox_y_max: float
    frame_number: int | None = None
    frame_timestamp_ms: int | None = None
    metadata: dict[str, Any] | None = None


def calculate_iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    """
    Calculate Intersection over Union (IoU) of two bounding boxes.
    Boxes are in format: (x_min, y_min, x_max, y_max)
    """
    x_min_a, y_min_a, x_max_a, y_max_a = box_a
    x_min_b, y_min_b, x_max_b, y_max_b = box_b

    # Intersection coordinates
    inter_x_min = max(x_min_a, x_min_b)
    inter_y_min = max(y_min_a, y_min_b)
    inter_x_max = min(x_max_a, x_max_b)
    inter_y_max = min(y_max_a, y_max_b)

    inter_w = max(0.0, inter_x_max - inter_x_min)
    inter_h = max(0.0, inter_y_max - inter_y_min)
    inter_area = inter_w * inter_h

    area_a = max(0.0, x_max_a - x_min_a) * max(0.0, y_max_a - y_min_a)
    area_b = max(0.0, x_max_b - x_min_b) * max(0.0, y_max_b - y_min_b)
    union_area = area_a + area_b - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


def apply_nms(
    detections: list[RawDetection],
    iou_threshold: float = 0.45,
) -> list[RawDetection]:
    """
    Performs class-aware Non-Maximum Suppression.
    For detections of the same damage class, suppresses overlapping boxes
    whose IoU exceeds `iou_threshold`, retaining the higher confidence detection.
    """
    if not detections:
        return []

    # Group by class
    by_class: dict[str, list[RawDetection]] = {}
    for d in detections:
        by_class.setdefault(d.damage_type_code, []).append(d)

    kept: list[RawDetection] = []

    for cls_dets in by_class.values():
        # Sort descending by confidence
        sorted_dets = sorted(cls_dets, key=lambda x: x.confidence, reverse=True)
        active_indices = list(range(len(sorted_dets)))

        while active_indices:
            best_idx = active_indices.pop(0)
            best_det = sorted_dets[best_idx]
            kept.append(best_det)

            remaining_indices = []
            best_box = (
                best_det.bbox_x_min,
                best_det.bbox_y_min,
                best_det.bbox_x_max,
                best_det.bbox_y_max,
            )

            for idx in active_indices:
                cand = sorted_dets[idx]
                cand_box = (
                    cand.bbox_x_min,
                    cand.bbox_y_min,
                    cand.bbox_x_max,
                    cand.bbox_y_max,
                )
                iou = calculate_iou(best_box, cand_box)
                if iou < iou_threshold:
                    remaining_indices.append(idx)

            active_indices = remaining_indices

    return kept


def suppress_temporal_duplicates(
    detections: list[RawDetection],
    time_window_ms: int = 2000,
    iou_threshold: float = 0.40,
) -> list[RawDetection]:
    """
    Suppresses video frame duplicate detections of the same damage occurring within
    a temporal window (`time_window_ms`) with high spatial overlap.
    """
    if not detections:
        return []

    # Sort chronologically, then by confidence
    sorted_dets = sorted(
        detections,
        key=lambda d: (d.frame_timestamp_ms or 0, -d.confidence),
    )

    result: list[RawDetection] = []

    for det in sorted_dets:
        is_duplicate = False
        det_box = (det.bbox_x_min, det.bbox_y_min, det.bbox_x_max, det.bbox_y_max)
        t_curr = det.frame_timestamp_ms or 0

        for existing in result:
            if existing.damage_type_code != det.damage_type_code:
                continue

            t_prev = existing.frame_timestamp_ms or 0
            if abs(t_curr - t_prev) <= time_window_ms:
                prev_box = (
                    existing.bbox_x_min,
                    existing.bbox_y_min,
                    existing.bbox_x_max,
                    existing.bbox_y_max,
                )
                if calculate_iou(prev_box, det_box) >= iou_threshold:
                    is_duplicate = True
                    break

        if not is_duplicate:
            result.append(det)

    return result
