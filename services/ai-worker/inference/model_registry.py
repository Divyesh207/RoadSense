from dataclasses import dataclass, field
from typing import Any, ClassVar

from inference.detector import BaseDetector, YOLODetector


@dataclass
class RegisteredModelInfo:
    model_id: str
    version: str
    name: str
    model_family: str
    model_type: str
    framework: str
    artifact_uri: str
    classes: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """Manages active AI models and cached detector instances."""

    _instance: ClassVar[Any] = None
    _models: ClassVar[dict[str, RegisteredModelInfo]] = {}
    _detectors: ClassVar[dict[str, BaseDetector]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_default_models()
        return cls._instance

    def _initialize_default_models(self) -> None:
        default_yolo = RegisteredModelInfo(
            model_id="road-damage-yolo-v8",
            version="1.0.0",
            name="Road Damage YOLOv8 Local",
            model_family="YOLO",
            model_type="OBJECT_DETECTION",
            framework="PyTorch",
            artifact_uri="local://models/yolov8_road_damage_v1.0.0.pt",
            classes=["POTHOLE", "CRACK", "DEPRESSION", "WATERLOGGING", "SURFACE_DAMAGE", "OTHER"],
            metrics={"mAP50": 0.884, "precision": 0.891, "recall": 0.842},
            metadata={"input_size": [640, 640], "trained_epochs": 100},
        )
        self.register_model(default_yolo)

    def register_model(self, info: RegisteredModelInfo) -> None:
        key = f"{info.model_id}:{info.version}"
        self._models[key] = info

    def get_model_info(self, model_id: str, version: str = "1.0.0") -> RegisteredModelInfo | None:
        key = f"{model_id}:{version}"
        return self._models.get(key)

    def get_detector(self, model_id: str = "road-damage-yolo-v8", version: str = "1.0.0") -> BaseDetector:
        key = f"{model_id}:{version}"
        if key not in self._detectors:
            info = self.get_model_info(model_id, version)
            classes = info.classes if info else None
            self._detectors[key] = YOLODetector(
                model_id=model_id,
                model_version=version,
                classes=classes,
            )
        return self._detectors[key]
