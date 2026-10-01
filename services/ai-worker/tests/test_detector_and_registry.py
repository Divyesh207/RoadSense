import cv2
import numpy as np
from inference.detector import YOLODetector
from inference.model_registry import ModelRegistry


def test_model_registry_default():
    registry = ModelRegistry()
    info = registry.get_model_info("road-damage-yolo-v8", "1.0.0")
    assert info is not None
    assert info.model_family == "YOLO"
    assert info.model_type == "OBJECT_DETECTION"
    assert "POTHOLE" in info.classes
    assert "mAP50" in info.metrics

    detector = registry.get_detector("road-damage-yolo-v8", "1.0.0")
    assert detector is not None


def test_yolo_detector_no_detections_on_uniform_road():
    detector = YOLODetector()
    # Uniform smooth asphalt image with no defects
    uniform_road = np.full((480, 640, 3), 110, dtype=np.uint8)
    res = detector.detect(uniform_road, confidence_threshold=0.30)
    assert res.model_id == "road-damage-yolo-v8"
    assert res.model_version == "1.0.0"
    assert res.inference_time_ms >= 0.0
    assert len(res.detections) == 0


def test_yolo_detector_identifies_defect_features():
    detector = YOLODetector()
    # Gray road with high-contrast pothole/sunken depression defect
    img = np.full((480, 640, 3), 140, dtype=np.uint8)
    cv2.circle(img, (320, 240), 60, (20, 20, 20), -1)  # Dark pothole
    cv2.circle(img, (320, 240), 65, (50, 50, 50), 4)

    res = detector.detect(img, confidence_threshold=0.25)
    assert len(res.detections) >= 1
    det = res.detections[0]
    assert det.damage_type_code in ("POTHOLE", "DEPRESSION")
    assert 0.0 <= det.confidence <= 1.0
    assert 0.0 <= det.bbox_x_min < det.bbox_x_max <= 1.0
    assert 0.0 <= det.bbox_y_min < det.bbox_y_max <= 1.0
