import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from postprocessing.nms import RawDetection, apply_nms

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    detections: list[RawDetection]
    model_id: str
    model_version: str
    inference_time_ms: float
    image_width: int
    image_height: int
    confidence_threshold: float
    raw_detections_count: int
    backend: str = "opencv-heuristic"
    backend_metadata: dict = field(default_factory=dict)


SUPPORTED_DAMAGE_CLASSES = [
    "POTHOLE",
    "CRACK",
    "DEPRESSION",
    "WATERLOGGING",
    "SURFACE_DAMAGE",
    "OTHER",
]

# Label names used by common road-damage datasets, mapped onto platform classes.
# RDD2020/RDD2022 codes: D00 longitudinal crack, D10 transverse crack,
# D20 alligator crack, D40 pothole.
CLASS_NAME_ALIASES: dict[str, str] = {
    "pothole": "POTHOLE",
    "potholes": "POTHOLE",
    "d40": "POTHOLE",
    "crack": "CRACK",
    "cracks": "CRACK",
    "longitudinal_crack": "CRACK",
    "transverse_crack": "CRACK",
    "alligator_crack": "CRACK",
    "d00": "CRACK",
    "d10": "CRACK",
    "d20": "CRACK",
    "depression": "DEPRESSION",
    "rutting": "DEPRESSION",
    "waterlogging": "WATERLOGGING",
    "water": "WATERLOGGING",
    "puddle": "WATERLOGGING",
    "surface_damage": "SURFACE_DAMAGE",
    "ravelling": "SURFACE_DAMAGE",
    "raveling": "SURFACE_DAMAGE",
    "patch": "SURFACE_DAMAGE",
}


def map_class_name(label: str) -> str:
    """Maps a model label (e.g. 'Pothole', 'D40', 'SURFACE_DAMAGE') to a platform class."""
    norm = label.strip().lower().replace(" ", "_").replace("-", "_")
    if norm.upper() in SUPPORTED_DAMAGE_CLASSES:
        return norm.upper()
    return CLASS_NAME_ALIASES.get(norm, "OTHER")


class BaseDetector(ABC):
    """Abstract interface for road damage object detectors."""

    model_id: str
    model_version: str
    backend: str

    @abstractmethod
    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        frame_number: int | None = None,
        frame_timestamp_ms: int | None = None,
    ) -> DetectionResult:
        pass


class ModelLoadError(RuntimeError):
    """Raised when YOLO weights are missing, unreadable, or not a detection model."""


class YOLODetector(BaseDetector):
    """
    Ultralytics YOLO (PyTorch) detector for trained road-damage weights.

    Requires a real weights file; there is no built-in fallback here. Use
    `inference.model_registry.ModelRegistry` to get the active detector, which
    falls back to `OpenCVHeuristicDetector` when no trained weights exist.
    """

    backend = "ultralytics-yolo"

    def __init__(
        self,
        weights_path: str,
        model_id: str = "road-damage-yolo",
        model_version: str = "unversioned",
        device: str = "cpu",
        image_size: int = 640,
    ):
        self.model_id = model_id
        self.model_version = model_version
        self.weights_path = weights_path
        self.device = device
        self.image_size = image_size
        self._model = self._load(weights_path)
        names = self._model.names
        self.class_names: dict[int, str] = dict(names) if isinstance(names, dict) else dict(enumerate(names))
        self.class_mapping: dict[int, str] = {idx: map_class_name(str(n)) for idx, n in self.class_names.items()}

    @staticmethod
    def _load(weights_path: str) -> Any:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ModelLoadError(f"ultralytics is not installed: {exc}") from exc
        try:
            model = YOLO(weights_path, task="detect")
        except Exception as exc:
            raise ModelLoadError(f"Could not load YOLO weights '{weights_path}': {exc}") from exc
        if getattr(model, "task", None) != "detect":
            raise ModelLoadError(f"Weights '{weights_path}' are a '{model.task}' model, expected 'detect'.")
        return model

    def results_to_detections(
        self,
        boxes_xyxyn: np.ndarray,
        confidences: np.ndarray,
        class_ids: np.ndarray,
        confidence_threshold: float,
        frame_number: int | None,
        frame_timestamp_ms: int | None,
    ) -> list[RawDetection]:
        detections: list[RawDetection] = []
        for (x1, y1, x2, y2), conf, cls_id in zip(boxes_xyxyn, confidences, class_ids, strict=True):
            conf_f = float(conf)
            if conf_f < confidence_threshold:
                continue
            x_min, y_min = max(0.0, float(x1)), max(0.0, float(y1))
            x_max, y_max = min(1.0, float(x2)), min(1.0, float(y2))
            if x_min >= x_max or y_min >= y_max:
                continue
            idx = int(cls_id)
            detections.append(
                RawDetection(
                    damage_type_code=self.class_mapping.get(idx, "OTHER"),
                    confidence=round(conf_f, 4),
                    bbox_x_min=round(x_min, 6),
                    bbox_y_min=round(y_min, 6),
                    bbox_x_max=round(x_max, 6),
                    bbox_y_max=round(y_max, 6),
                    frame_number=frame_number,
                    frame_timestamp_ms=frame_timestamp_ms,
                    metadata={"model_class_id": idx, "model_class_name": self.class_names.get(idx, str(idx))},
                )
            )
        return detections

    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        frame_number: int | None = None,
        frame_timestamp_ms: int | None = None,
    ) -> DetectionResult:
        t_start = time.perf_counter()
        h, w = image.shape[:2]
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

        results = self._model.predict(
            image,
            conf=confidence_threshold,
            iou=iou_threshold,
            imgsz=self.image_size,
            device=self.device,
            verbose=False,
        )
        boxes = results[0].boxes
        raw = self.results_to_detections(
            boxes.xyxyn.cpu().numpy(),
            boxes.conf.cpu().numpy(),
            boxes.cls.cpu().numpy(),
            confidence_threshold,
            frame_number,
            frame_timestamp_ms,
        )
        filtered = apply_nms(raw, iou_threshold=iou_threshold)

        return DetectionResult(
            detections=filtered,
            model_id=self.model_id,
            model_version=self.model_version,
            inference_time_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
            image_width=w,
            image_height=h,
            confidence_threshold=confidence_threshold,
            raw_detections_count=len(raw),
            backend=self.backend,
            backend_metadata={"weights_path": self.weights_path, "device": self.device},
        )


class OpenCVHeuristicDetector(BaseDetector):
    """
    Deterministic OpenCV contour analyzer used when no trained YOLO weights are
    available. It is NOT a trained model: results are rule-based candidates and
    are labelled with their own model id/backend so they are never mistaken for
    YOLO output in AIProcessingRun provenance.
    """

    backend = "opencv-heuristic"

    def __init__(
        self,
        model_id: str = "opencv-heuristic-road-damage",
        model_version: str = "1.0.0",
        fallback_reason: str | None = None,
    ):
        self.model_id = model_id
        self.model_version = model_version
        self.fallback_reason = fallback_reason

    def detect(
        self,
        image: np.ndarray,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        frame_number: int | None = None,
        frame_timestamp_ms: int | None = None,
    ) -> DetectionResult:
        t_start = time.perf_counter()
        h, w = image.shape[:2]

        raw_detections: list[RawDetection] = []

        # Analyzes contrast, dark depressions (potholes) and structural edges (cracks)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        blur = cv2.GaussianBlur(gray, (5, 5), 0)

        # Pothole / Depression detection via adaptive thresholding and contour analysis
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 8
        )
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Ignore tiny noise or whole-image artifacts (> 40% of image)
            if area < 250 or area > (w * h * 0.40):
                continue

            bx, by, bw, bh = cv2.boundingRect(cnt)
            x_min = max(0.0, bx / float(w))
            y_min = max(0.0, by / float(h))
            x_max = min(1.0, (bx + bw) / float(w))
            y_max = min(1.0, (by + bh) / float(h))

            if x_min >= x_max or y_min >= y_max:
                continue

            aspect = float(bw) / float(bh) if bh > 0 else 1.0
            extent = float(area) / float(bw * bh) if (bw * bh) > 0 else 0.0

            # Classification based on geometric shape & contour properties
            if aspect > 3.0 or aspect < 0.33:
                cls_code = "CRACK"
                base_conf = 0.55 + min(0.35, extent * 0.4)
            elif extent > 0.55:
                cls_code = "POTHOLE"
                base_conf = 0.60 + min(0.35, (area / (w * h * 0.10)) * 0.3)
            elif extent > 0.35:
                cls_code = "DEPRESSION"
                base_conf = 0.50 + min(0.30, extent * 0.3)
            else:
                cls_code = "SURFACE_DAMAGE"
                base_conf = 0.45

            confidence = round(min(0.98, max(0.10, base_conf)), 4)

            if confidence >= confidence_threshold:
                raw_detections.append(
                    RawDetection(
                        damage_type_code=cls_code,
                        confidence=confidence,
                        bbox_x_min=round(x_min, 6),
                        bbox_y_min=round(y_min, 6),
                        bbox_x_max=round(x_max, 6),
                        bbox_y_max=round(y_max, 6),
                        frame_number=frame_number,
                        frame_timestamp_ms=frame_timestamp_ms,
                        metadata={"area_px": int(area), "aspect_ratio": round(aspect, 2)},
                    )
                )

        raw_count = len(raw_detections)
        # Apply class-aware Non-Maximum Suppression
        filtered_detections = apply_nms(raw_detections, iou_threshold=iou_threshold)

        return DetectionResult(
            detections=filtered_detections,
            model_id=self.model_id,
            model_version=self.model_version,
            inference_time_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
            image_width=w,
            image_height=h,
            confidence_threshold=confidence_threshold,
            raw_detections_count=raw_count,
            backend=self.backend,
            backend_metadata={"fallback_reason": self.fallback_reason} if self.fallback_reason else {},
        )
