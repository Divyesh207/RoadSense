from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    damages,
    gis,
    health,
    inspections,
    jobs,
    maintenance,
    predictions,
    road_health,
    roads,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(roads.router, prefix="/roads", tags=["Roads"])
api_router.include_router(roads.segments_router, prefix="/road-segments", tags=["Road Segments"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Processing Jobs"])
api_router.include_router(damages.types_router, prefix="/damage-types", tags=["Damage Types"])
api_router.include_router(damages.router, prefix="/damages", tags=["Damages"])
api_router.include_router(gis.router, prefix="/map", tags=["GIS Map"])
api_router.include_router(road_health.road_health_router, prefix="/roads", tags=["Road Health"])
api_router.include_router(road_health.segment_health_router, prefix="/road-segments", tags=["Road Health"])
api_router.include_router(predictions.router, prefix="/road-segments", tags=["Predictions"])
api_router.include_router(maintenance.router, prefix="/maintenance-jobs", tags=["Maintenance"])
