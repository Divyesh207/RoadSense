import math
from typing import Any

import shapely
from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import to_shape
from shapely.geometry import LineString, mapping, shape

from app.schemas.road import GeoJSONLineString


def geometry_to_geojson(geom: Any) -> dict[str, Any] | None:
    """Convert a database geometry element or string into a GeoJSON dictionary."""
    if geom is None:
        return None
    try:
        if isinstance(geom, (WKBElement, WKTElement)):
            s = to_shape(geom)
            return mapping(s)
        if isinstance(geom, str):
            s = shapely.from_wkt(geom)
            return mapping(s)
        if hasattr(geom, "__geo_interface__"):
            return geom.__geo_interface__
    except (ValueError, TypeError, AttributeError):
        return None
    return None


def geojson_to_wkt(geom_input: GeoJSONLineString | dict[str, Any] | None) -> str | None:
    """Validate and convert GeoJSON input into WKT LINESTRING format."""
    if geom_input is None:
        return None
    if isinstance(geom_input, GeoJSONLineString):
        coords = geom_input.coordinates
    elif isinstance(geom_input, dict):
        s = shape(geom_input)
        if not isinstance(s, LineString):
            raise TypeError("Geometry must be a valid GeoJSON LineString.")
        return s.wkt
    else:
        return None

    if len(coords) < 2:
        raise ValueError("LineString requires at least 2 points.")
    pts_str = ", ".join(f"{pt[0]} {pt[1]}" for pt in coords)
    return f"LINESTRING({pts_str})"


def point_to_wkt(lat: float, lon: float) -> str:
    """Convert latitude and longitude to WKT POINT(longitude latitude)."""
    return f"POINT({lon} {lat})"


def wkt_or_geom_to_point(geom: Any) -> tuple[float, float] | None:
    """Extract (latitude, longitude) from a database geometry element or WKT string."""
    if geom is None:
        return None
    try:
        if isinstance(geom, (WKBElement, WKTElement)):
            pt = to_shape(geom)
            return float(pt.y), float(pt.x)
        if isinstance(geom, str):
            pt = shapely.from_wkt(geom)
            return float(pt.y), float(pt.x)
    except (ValueError, TypeError, AttributeError, shapely.GEOSException):
        return None
    return None



def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in meters."""
    r_earth = 6371000.0  # Earth's radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_earth * c


def point_to_segment_distance_m(
    p_lat: float, p_lon: float, a_lat: float, a_lon: float, b_lat: float, b_lon: float
) -> float:
    """Calculate the shortest distance in meters from point P to line segment AB."""
    ab_dist = haversine_distance_m(a_lat, a_lon, b_lat, b_lon)
    if ab_dist < 1e-6:
        return haversine_distance_m(p_lat, p_lon, a_lat, a_lon)

    # Approximate local projection around point A
    cos_lat = math.cos(math.radians((a_lat + b_lat) / 2.0))
    dx = (b_lon - a_lon) * 111320.0 * cos_lat
    dy = (b_lat - a_lat) * 110540.0
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq < 1e-6:
        return haversine_distance_m(p_lat, p_lon, a_lat, a_lon)

    px = (p_lon - a_lon) * 111320.0 * cos_lat
    py = (p_lat - a_lat) * 110540.0

    # Projection factor clamped to segment [0, 1]
    t = max(0.0, min(1.0, (px * dx + py * dy) / seg_len_sq))

    proj_x = t * dx
    proj_y = t * dy

    return math.hypot(px - proj_x, py - proj_y)


def point_to_linestring_distance_m(
    lat: float, lon: float, geom_data: Any
) -> float | None:
    """Calculate minimum distance in meters between a GPS point and a LineString."""
    geojson = geometry_to_geojson(geom_data)
    if not geojson or geojson.get("type") != "LineString":
        return None

    coords = geojson.get("coordinates", [])
    if len(coords) < 2:
        return None

    min_dist = float("inf")
    for i in range(len(coords) - 1):
        p1_lon, p1_lat = coords[i][0], coords[i][1]
        p2_lon, p2_lat = coords[i + 1][0], coords[i + 1][1]
        d = point_to_segment_distance_m(lat, lon, p1_lat, p1_lon, p2_lat, p2_lon)
        min_dist = min(min_dist, d)

    return min_dist


def bbox_intersects_linestring(
    geom_data: Any, min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> bool:
    """Check whether a LineString's bounding box intersects the given [min_lat, min_lon, max_lat, max_lon] window."""
    geojson = geometry_to_geojson(geom_data)
    if not geojson or geojson.get("type") != "LineString":
        return False

    coords = geojson.get("coordinates", [])
    if not coords:
        return False

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    g_min_lon, g_max_lon = min(lons), max(lons)
    g_min_lat, g_max_lat = min(lats), max(lats)

    # Check for non-overlap
    if g_max_lon < min_lon or g_min_lon > max_lon:
        return False
    return not (g_max_lat < min_lat or g_min_lat > max_lat)

