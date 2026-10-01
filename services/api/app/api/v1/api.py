from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, inspections, jobs, roads

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(roads.router, prefix="/roads", tags=["Roads"])
api_router.include_router(roads.segments_router, prefix="/road-segments", tags=["Road Segments"])
api_router.include_router(inspections.router, prefix="/inspections", tags=["Inspections"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Processing Jobs"])



