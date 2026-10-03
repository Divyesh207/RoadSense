from dataclasses import dataclass
from typing import Any


@dataclass
class SeverityAssessment:
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    score: float  # 0.0 to 1.0
    contributing_factors: dict[str, Any]
    formula_version: str = "1.0.0"


# Base severity weights by damage type code
DAMAGE_TYPE_SEVERITY_WEIGHTS: dict[str, float] = {
    "POTHOLE": 0.85,
    "DEPRESSION": 0.75,
    "WATERLOGGING": 0.70,
    "CRACK": 0.50,
    "SURFACE_DAMAGE": 0.40,
    "OTHER": 0.30,
}


def assess_damage_severity(
    damage_type_code: str,
    bbox_x_min: float,
    bbox_y_min: float,
    bbox_x_max: float,
    bbox_y_max: float,
    pixel_width: int | None = None,
    pixel_height: int | None = None,
) -> SeverityAssessment:
    """
    Computes physical damage severity based on measurable geometric and class factors.
    Returns structured SeverityAssessment with full factor explanation.
    """
    # 1. Bounding box relative area
    width_ratio = max(0.0, bbox_x_max - bbox_x_min)
    height_ratio = max(0.0, bbox_y_max - bbox_y_min)
    area_ratio = width_ratio * height_ratio

    # 2. Damage type inherent weight
    type_weight = DAMAGE_TYPE_SEVERITY_WEIGHTS.get(damage_type_code.upper(), 0.40)

    # 3. Area severity component (scaling: 0.01 is small, 0.15+ is large damage in road frame)
    # Clamp area factor to 1.0
    area_factor = min(1.0, area_ratio / 0.15)

    # 4. Aspect ratio distortion penalty (very wide cracks or large elongated depressions)
    aspect_ratio = (width_ratio / height_ratio) if height_ratio > 0 else 1.0

    # 5. Composite severity score (60% physical area + 40% damage hazard class weight)
    composite_score = round((0.60 * area_factor) + (0.40 * type_weight), 4)

    # 6. Categorize into LOW / MEDIUM / HIGH / CRITICAL
    if composite_score >= 0.75:
        severity = "CRITICAL"
    elif composite_score >= 0.50:
        severity = "HIGH"
    elif composite_score >= 0.25:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    factors = {
        # Deterministic rule over bounding-box size and damage class, not a learned model.
        "method": "RULE_BASED",
        "damage_type_code": damage_type_code,
        "type_weight": type_weight,
        "normalized_area": round(area_ratio, 6),
        "area_factor": round(area_factor, 4),
        "width_ratio": round(width_ratio, 4),
        "height_ratio": round(height_ratio, 4),
        "aspect_ratio": round(aspect_ratio, 3),
        "pixel_dimensions": {
            "width": pixel_width,
            "height": pixel_height,
        }
        if pixel_width and pixel_height
        else None,
    }

    return SeverityAssessment(
        severity=severity,
        score=composite_score,
        contributing_factors=factors,
        formula_version="1.0.0",
    )
