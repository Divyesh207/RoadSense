from postprocessing.nms import (
    RawDetection,
    apply_nms,
    calculate_iou,
    suppress_temporal_duplicates,
)
from postprocessing.severity import assess_damage_severity


def test_calculate_iou():
    box1 = (0.1, 0.1, 0.5, 0.5)
    box2 = (0.1, 0.1, 0.5, 0.5)
    assert calculate_iou(box1, box2) == 1.0

    # Disjoint boxes
    box3 = (0.6, 0.6, 0.9, 0.9)
    assert calculate_iou(box1, box3) == 0.0

    # Partial overlap
    box4 = (0.3, 0.1, 0.7, 0.5)
    iou = calculate_iou(box1, box4)
    assert 0.0 < iou < 1.0


def test_apply_nms():
    # Two overlapping detections of same class: higher confidence kept
    det1 = RawDetection("POTHOLE", 0.90, 0.1, 0.1, 0.5, 0.5)
    det2 = RawDetection("POTHOLE", 0.60, 0.12, 0.12, 0.52, 0.52)  # High IoU with det1
    det3 = RawDetection("CRACK", 0.75, 0.11, 0.11, 0.51, 0.51)  # High IoU but DIFFERENT class
    det4 = RawDetection("POTHOLE", 0.85, 0.7, 0.7, 0.9, 0.9)  # Non-overlapping pothole

    kept = apply_nms([det1, det2, det3, det4], iou_threshold=0.45)

    # det2 must be suppressed, det1, det3, det4 must be kept
    assert len(kept) == 3
    classes_and_confs = [(d.damage_type_code, d.confidence) for d in kept]
    assert ("POTHOLE", 0.90) in classes_and_confs
    assert ("CRACK", 0.75) in classes_and_confs
    assert ("POTHOLE", 0.85) in classes_and_confs
    assert ("POTHOLE", 0.60) not in classes_and_confs


def test_suppress_temporal_duplicates():
    # Video detections of same damage in consecutive frames
    det1 = RawDetection("POTHOLE", 0.88, 0.2, 0.2, 0.4, 0.4, frame_number=0, frame_timestamp_ms=0)
    det2 = RawDetection("POTHOLE", 0.85, 0.21, 0.21, 0.41, 0.41, frame_number=1, frame_timestamp_ms=500)
    # Different damage much later
    det3 = RawDetection("POTHOLE", 0.80, 0.2, 0.2, 0.4, 0.4, frame_number=10, frame_timestamp_ms=5000)

    filtered = suppress_temporal_duplicates([det1, det2, det3], time_window_ms=2000, iou_threshold=0.40)
    assert len(filtered) == 2
    assert filtered[0].frame_timestamp_ms == 0
    assert filtered[1].frame_timestamp_ms == 5000


def test_assess_damage_severity():
    # Large pothole
    sev_large = assess_damage_severity("POTHOLE", 0.1, 0.1, 0.6, 0.6, pixel_width=640, pixel_height=480)
    assert sev_large.severity in ("HIGH", "CRITICAL")
    assert sev_large.contributing_factors["damage_type_code"] == "POTHOLE"
    assert sev_large.contributing_factors["normalized_area"] > 0.10

    # Small surface crack
    sev_small = assess_damage_severity("SURFACE_DAMAGE", 0.1, 0.1, 0.15, 0.15)
    assert sev_small.severity in ("LOW", "MEDIUM")
    assert sev_small.score < sev_large.score
