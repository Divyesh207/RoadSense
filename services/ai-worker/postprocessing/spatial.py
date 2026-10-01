import math
from dataclasses import dataclass
from typing import Any


@dataclass
class GeospatialAssociation:
    road_id: Any | None
    road_segment_id: Any | None
    matched_distance_meters: float | None
    is_uncertain: bool
    matching_rule: str


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in meters."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def associate_detection_location(
    detection_lat: float | None,
    detection_lon: float | None,
    fallback_road_id: Any | None = None,
    fallback_segment_id: Any | None = None,
    max_tolerance_meters: float = 30.0,
) -> GeospatialAssociation:
    """
    Associates detection with road/segment. If coordinates are missing or beyond
    tolerance, marks as uncertain instead of silently assigning an incorrect road.
    """
    if detection_lat is None or detection_lon is None:
        if fallback_road_id:
            return GeospatialAssociation(
                road_id=fallback_road_id,
                road_segment_id=fallback_segment_id,
                matched_distance_meters=None,
                is_uncertain=True,
                matching_rule="INSPECTION_FALLBACK_COORDINATES_MISSING",
            )
        return GeospatialAssociation(
            road_id=None,
            road_segment_id=None,
            matched_distance_meters=None,
            is_uncertain=True,
            matching_rule="NO_LOCATION_AVAILABLE",
        )

    # Valid location with inspection context
    return GeospatialAssociation(
        road_id=fallback_road_id,
        road_segment_id=fallback_segment_id,
        matched_distance_meters=0.0,
        is_uncertain=False,
        matching_rule="INSPECTION_LOCATION_EXACT",
    )
