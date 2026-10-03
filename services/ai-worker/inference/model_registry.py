"""
Active-model selection for the AI worker.

Trained road-damage weights are NOT shipped with the repository. The registry
looks for a YOLO weights file at YOLO_MODEL_PATH (default
<AI_MODEL_DIR>/pothole_yolov8.pt). Provenance (model id, version, metrics,
training notes) is read only from an optional sidecar JSON next to the weights
(`<weights>.json`); nothing is invented when it is absent.

If the weights are missing or fail to load, the deterministic
OpenCVHeuristicDetector is used and `inference_status()` reports
mode=FALLBACK with the reason. Set AI_REQUIRE_TRAINED_MODEL=true (staging /
production) to fail instead of silently falling back.
"""

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from inference.detector import (
    SUPPORTED_DAMAGE_CLASSES,
    BaseDetector,
    ModelLoadError,
    OpenCVHeuristicDetector,
    YOLODetector,
)

logger = logging.getLogger(__name__)

FALLBACK_MODEL_ID = "opencv-heuristic-road-damage"
FALLBACK_MODEL_VERSION = "1.0.0"
DEFAULT_YOLO_MODEL_ID = "road-damage-yolo"


class TrainedModelRequiredError(RuntimeError):
    """Raised when AI_REQUIRE_TRAINED_MODEL is set but no usable YOLO weights exist."""


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


@dataclass
class InferenceStatus:
    mode: str  # "YOLO" or "FALLBACK"
    model_id: str
    model_version: str
    weights_path: str
    weights_present: bool
    reason: str | None = None


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def default_weights_path() -> Path:
    explicit = os.getenv("YOLO_MODEL_PATH")
    if explicit:
        return Path(explicit)
    return Path(os.getenv("AI_MODEL_DIR", "./data/models")) / "pothole_yolov8.pt"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_sidecar(weights: Path) -> dict[str, Any]:
    sidecar = weights.with_suffix(weights.suffix + ".json")
    if not sidecar.is_file():
        return {}
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Ignoring unreadable model metadata %s: %s", sidecar, exc)
        return {}
    return data if isinstance(data, dict) else {}


class ModelRegistry:
    """Selects the active detector and records model provenance."""

    _instance: ClassVar[Any] = None
    _models: ClassVar[dict[str, RegisteredModelInfo]] = {}
    _detectors: ClassVar[dict[str, BaseDetector]] = {}
    _active: ClassVar[BaseDetector | None] = None
    _status: ClassVar[InferenceStatus | None] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_fallback_model()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Drops cached state (used by tests and after weights are replaced)."""
        cls._instance = None
        cls._models = {}
        cls._detectors = {}
        cls._active = None
        cls._status = None

    def _register_fallback_model(self) -> None:
        self.register_model(
            RegisteredModelInfo(
                model_id=FALLBACK_MODEL_ID,
                version=FALLBACK_MODEL_VERSION,
                name="OpenCV Heuristic Road Damage Analyzer",
                model_family="OPENCV_HEURISTIC",
                model_type="OBJECT_DETECTION",
                framework="OpenCV",
                artifact_uri="builtin://inference/detector.py#OpenCVHeuristicDetector",
                classes=list(SUPPORTED_DAMAGE_CLASSES),
                metrics={},
                metadata={
                    "trained": False,
                    "description": "Deterministic contour heuristic; not a trained model. "
                    "Used only when no trained YOLO weights are available.",
                },
            )
        )

    def register_model(self, info: RegisteredModelInfo) -> None:
        self._models[f"{info.model_id}:{info.version}"] = info

    def get_model_info(self, model_id: str, version: str) -> RegisteredModelInfo | None:
        return self._models.get(f"{model_id}:{version}")

    def _load_yolo(self, weights: Path) -> YOLODetector:
        sidecar = _read_sidecar(weights)
        sha = _sha256(weights)
        threshold = (sidecar.get("training") or {}).get("confidence_threshold", {}).get("value")
        model_id = str(sidecar.get("model_id") or DEFAULT_YOLO_MODEL_ID)
        version = str(sidecar.get("version") or f"sha256-{sha[:12]}")
        detector = YOLODetector(
            weights_path=str(weights),
            model_id=model_id,
            model_version=version,
            device=os.getenv("AI_DEVICE", "cpu"),
            image_size=int(sidecar.get("input_size") or 640),
            recommended_confidence_threshold=float(threshold) if threshold is not None else None,
        )
        self.register_model(
            RegisteredModelInfo(
                model_id=model_id,
                version=version,
                name=str(sidecar.get("name") or f"YOLO road damage ({weights.name})"),
                model_family="YOLO",
                model_type="OBJECT_DETECTION",
                framework="PyTorch/Ultralytics",
                artifact_uri=f"file://{weights.as_posix()}",
                classes=sorted(set(detector.class_mapping.values())),
                metrics=dict(sidecar.get("metrics") or {}),
                metadata={
                    "trained": True,
                    "weights_sha256": sha,
                    "model_class_names": {str(k): v for k, v in detector.class_names.items()},
                    "class_mapping": {str(k): v for k, v in detector.class_mapping.items()},
                    **({"training": sidecar["training"]} if "training" in sidecar else {}),
                },
            )
        )
        return detector

    def get_detector(self) -> BaseDetector:
        """Returns the active detector: trained YOLO weights when present and
        loadable, otherwise the OpenCV heuristic fallback (unless strict)."""
        if self._active is not None:
            return self._active

        weights = default_weights_path()
        present = weights.is_file()
        reason: str | None = None
        if present:
            try:
                detector: BaseDetector = self._load_yolo(weights)
                type(self)._status = InferenceStatus(
                    "YOLO", detector.model_id, detector.model_version, str(weights), True
                )
                type(self)._active = detector
                logger.info("Inference mode YOLO: %s (%s)", weights, detector.model_version)
                return detector
            except (ModelLoadError, OSError) as exc:
                reason = str(exc)
        else:
            reason = f"Trained weights not found at {weights}"

        if _env_flag("AI_REQUIRE_TRAINED_MODEL"):
            raise TrainedModelRequiredError(reason)

        logger.warning("Inference mode FALLBACK (OpenCV heuristic): %s", reason)
        detector = OpenCVHeuristicDetector(FALLBACK_MODEL_ID, FALLBACK_MODEL_VERSION, fallback_reason=reason)
        type(self)._status = InferenceStatus(
            "FALLBACK", FALLBACK_MODEL_ID, FALLBACK_MODEL_VERSION, str(weights), present, reason
        )
        type(self)._active = detector
        return detector

    def inference_status(self) -> dict[str, Any]:
        if self._status is None:
            try:
                self.get_detector()
            except TrainedModelRequiredError as exc:
                return asdict(
                    InferenceStatus("UNAVAILABLE", "", "", str(default_weights_path()), False, str(exc))
                )
        return asdict(self._status)
