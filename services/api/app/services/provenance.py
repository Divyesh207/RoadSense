"""
Honest labelling of how an AI detection was produced.

The worker records the detector that actually ran on each AIProcessingRun
(ai_models row). The OpenCV fallback (model_family OPENCV_HEURISTIC) is a
deterministic contour heuristic, not a trained model: its per-detection
"confidence" is a shape-derived score, not a model probability.
"""

from typing import Any

HEURISTIC_MODEL_FAMILIES = {"OPENCV_HEURISTIC"}

DETECTION_METHOD_HEURISTIC = "HEURISTIC_FALLBACK"
DETECTION_METHOD_TRAINED = "TRAINED_MODEL"
DETECTION_METHOD_UNKNOWN = "UNKNOWN"

SCORE_TYPE_HEURISTIC = "HEURISTIC_SCORE"
SCORE_TYPE_MODEL = "MODEL_CONFIDENCE"


def detection_provenance(model: Any | None) -> dict[str, str | None]:
    """Returns detection_method, score_type, model_name and model_version for an AIModel (or None)."""
    if model is None:
        return {
            "detection_method": DETECTION_METHOD_UNKNOWN,
            "score_type": None,
            "model_name": None,
            "model_version": None,
        }
    metadata = getattr(model, "metadata_", None) or {}
    heuristic = model.model_family in HEURISTIC_MODEL_FAMILIES or metadata.get("trained") is False
    return {
        "detection_method": DETECTION_METHOD_HEURISTIC if heuristic else DETECTION_METHOD_TRAINED,
        "score_type": SCORE_TYPE_HEURISTIC if heuristic else SCORE_TYPE_MODEL,
        "model_name": model.name,
        "model_version": model.version,
    }
