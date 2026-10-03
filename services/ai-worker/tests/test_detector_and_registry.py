import json

import cv2
import numpy as np
import pytest

from inference.detector import OpenCVHeuristicDetector, YOLODetector, map_class_name
from inference.model_registry import (
    FALLBACK_MODEL_ID,
    FALLBACK_MODEL_VERSION,
    ModelRegistry,
    TrainedModelRequiredError,
)
from pipelines.media_pipeline import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    resolve_confidence_threshold,
)


def test_registry_falls_back_and_reports_missing_weights(tmp_path, monkeypatch):
    monkeypatch.setenv("YOLO_MODEL_PATH", str(tmp_path / "absent.pt"))
    registry = ModelRegistry()

    detector = registry.get_detector()

    assert isinstance(detector, OpenCVHeuristicDetector)
    status = registry.inference_status()
    assert status["mode"] == "FALLBACK"
    assert status["weights_present"] is False
    assert "not found" in status["reason"]

    info = registry.get_model_info(FALLBACK_MODEL_ID, FALLBACK_MODEL_VERSION)
    assert info.model_family == "OPENCV_HEURISTIC"
    assert info.metrics == {}  # no accuracy claims for an untrained heuristic
    assert info.metadata["trained"] is False


def test_registry_falls_back_on_unloadable_weights(tmp_path, monkeypatch):
    bogus = tmp_path / "pothole_yolov8.pt"
    bogus.write_bytes(b"this is not a torch checkpoint")
    monkeypatch.setenv("YOLO_MODEL_PATH", str(bogus))

    detector = ModelRegistry().get_detector()

    assert isinstance(detector, OpenCVHeuristicDetector)
    status = ModelRegistry().inference_status()
    assert status["mode"] == "FALLBACK"
    assert status["weights_present"] is True
    assert "Could not load YOLO weights" in status["reason"]


def test_strict_mode_refuses_to_fall_back(tmp_path, monkeypatch):
    monkeypatch.setenv("YOLO_MODEL_PATH", str(tmp_path / "absent.pt"))
    monkeypatch.setenv("AI_REQUIRE_TRAINED_MODEL", "true")

    with pytest.raises(TrainedModelRequiredError):
        ModelRegistry().get_detector()
    assert ModelRegistry().inference_status()["mode"] == "UNAVAILABLE"


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("pothole", "POTHOLE"),
        ("D40", "POTHOLE"),
        ("Alligator crack", "CRACK"),
        ("D00", "CRACK"),
        ("SURFACE_DAMAGE", "SURFACE_DAMAGE"),
        ("car", "OTHER"),
    ],
)
def test_model_label_mapping(label, expected):
    assert map_class_name(label) == expected


def test_yolo_result_conversion_filters_and_maps_boxes():
    detector = YOLODetector.__new__(YOLODetector)  # skip weight loading; test conversion only
    detector.class_names = {0: "D00", 1: "D40"}
    detector.class_mapping = {0: "CRACK", 1: "POTHOLE"}

    dets = detector.results_to_detections(
        boxes_xyxyn=np.array([[0.1, 0.2, 0.4, 0.5], [0.5, 0.5, 0.9, 1.2], [0.3, 0.3, 0.3, 0.6]]),
        confidences=np.array([0.91, 0.66, 0.80]),
        class_ids=np.array([1, 0, 0]),
        confidence_threshold=0.5,
        frame_number=7,
        frame_timestamp_ms=7000,
    )

    # Third box is degenerate (zero width) and dropped; second box is clipped to 1.0.
    assert [d.damage_type_code for d in dets] == ["POTHOLE", "CRACK"]
    assert dets[0].confidence == 0.91
    assert dets[1].bbox_y_max == 1.0
    assert dets[0].frame_number == 7
    assert dets[0].metadata == {"model_class_id": 1, "model_class_name": "D40"}


def test_ultralytics_inference_path_with_untrained_architecture(tmp_path, monkeypatch):
    """Exercises the real Ultralytics load + predict path end-to-end.

    The weights are a randomly initialised YOLOv8n built from the bundled
    architecture YAML, created only inside tmp_path. They are NOT a road-damage
    model; this test verifies wiring and provenance, not detection accuracy.
    """
    ultralytics = pytest.importorskip("ultralytics")
    weights = tmp_path / "pothole_yolov8.pt"
    ultralytics.YOLO("yolov8n.yaml").save(str(weights))
    weights.with_suffix(".pt.json").write_text(
        json.dumps({
            "model_id": "untrained-test-yolo",
            "version": "0.0.0-test",
            "metrics": {},
            "training": {"confidence_threshold": {"value": 0.31}},
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("YOLO_MODEL_PATH", str(weights))

    registry = ModelRegistry()
    detector = registry.get_detector()

    assert isinstance(detector, YOLODetector)
    assert registry.inference_status()["mode"] == "YOLO"
    info = registry.get_model_info("untrained-test-yolo", "0.0.0-test")
    assert info.model_family == "YOLO"
    assert len(info.metadata["weights_sha256"]) == 64
    # Validation-selected threshold from the sidecar is used when no explicit threshold is given
    assert detector.recommended_confidence_threshold == 0.31
    assert resolve_confidence_threshold(None, detector) == 0.31
    assert resolve_confidence_threshold(0.5, detector) == 0.5

    result = detector.detect(np.full((480, 640, 3), 120, dtype=np.uint8), confidence_threshold=0.25)
    assert result.backend == "ultralytics-yolo"
    assert result.model_id == "untrained-test-yolo"
    assert result.model_version == "0.0.0-test"
    for det in result.detections:
        assert 0.0 <= det.bbox_x_min < det.bbox_x_max <= 1.0


def test_heuristic_detector_no_detections_on_uniform_road():
    detector = OpenCVHeuristicDetector()
    uniform_road = np.full((480, 640, 3), 110, dtype=np.uint8)
    res = detector.detect(uniform_road, confidence_threshold=0.30)
    assert res.model_id == FALLBACK_MODEL_ID
    assert res.model_version == FALLBACK_MODEL_VERSION
    assert res.backend == "opencv-heuristic"
    assert res.inference_time_ms >= 0.0
    assert len(res.detections) == 0


def test_heuristic_detector_identifies_defect_features():
    detector = OpenCVHeuristicDetector()
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


def test_threshold_resolution_without_model_recommendation():
    heuristic = OpenCVHeuristicDetector()
    assert heuristic.recommended_confidence_threshold is None
    assert resolve_confidence_threshold(None, heuristic) == DEFAULT_CONFIDENCE_THRESHOLD == 0.25
    assert resolve_confidence_threshold(0.4, heuristic) == 0.4
