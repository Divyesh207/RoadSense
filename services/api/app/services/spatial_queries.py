"""PostGIS-backed spatial queries (PostgreSQL only).

Distances are computed on the geography type (metres on the WGS84 spheroid).
Each query first applies a bounding-box `&&` filter on the geometry column so
the GIST index on road_segments.geometry is used; the exact ST_DWithin test on
geography runs only on the index candidates.
"""

import math
import uuid
from dataclasses import dataclass

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.road import Road, RoadSegment

METRES_PER_DEGREE_LAT = 110_540.0
METRES_PER_DEGREE_LON_EQUATOR = 111_320.0


@dataclass
class SegmentMatch:
    segment: RoadSegment
    distance_m: float
    # Fraction (0..1) along the segment of the closest point (ST_LineLocatePoint)
    position_along_segment: float


def is_postgres(db: AsyncSession) -> bool:
    return db.get_bind().dialect.name == "postgresql"


def degree_padding(latitude: float, distance_m: float) -> tuple[float, float]:
    """Degrees of longitude/latitude that safely cover distance_m around latitude."""
    pad_lat = distance_m / METRES_PER_DEGREE_LAT * 1.1
    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    pad_lon = distance_m / (METRES_PER_DEGREE_LON_EQUATOR * cos_lat) * 1.1
    return pad_lon, pad_lat


async def match_segments_postgis(
    db: AsyncSession,
    organization_id: uuid.UUID,
    latitude: float,
    longitude: float,
    max_distance_m: float,
) -> list[SegmentMatch]:
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    seg_geog = cast(RoadSegment.geometry, Geography(srid=4326))
    point_geog = cast(point, Geography(srid=4326))
    pad_lon, pad_lat = degree_padding(latitude, max_distance_m)

    distance = func.ST_Distance(seg_geog, point_geog).label("distance_m")
    position = func.ST_LineLocatePoint(RoadSegment.geometry, point).label("position")

    stmt = (
        select(RoadSegment, distance, position)
        .join(Road, RoadSegment.road_id == Road.id)
        .where(
            RoadSegment.organization_id == organization_id,
            RoadSegment.is_active.is_(True),
            Road.is_active.is_(True),
            RoadSegment.geometry.is_not(None),
            RoadSegment.geometry.op("&&")(func.ST_Expand(point, pad_lon, pad_lat)),
            func.ST_DWithin(seg_geog, point_geog, max_distance_m),
        )
        .options(selectinload(RoadSegment.road))
        .order_by(distance)
    )
    rows = (await db.execute(stmt)).all()
    return [SegmentMatch(seg, float(dist), float(pos)) for seg, dist, pos in rows]
