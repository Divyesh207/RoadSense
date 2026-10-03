import uuid

from pydantic import BaseModel, Field


class DashboardSummaryData(BaseModel):
    total_roads: int
    total_segments: int
    active_inspections: int
    open_damages: int
    high_severity_damages: int
    critical_damages: int
    maintenance_open: int
    maintenance_in_progress: int
    verification_pending: int
    verified_repairs: int
    recurrence_count: int
    average_road_health: float | None = None
    # Phase 3C additions (all counted from stored records)
    pending_review_damages: int = 0
    maintenance_by_status: dict[str, int] = Field(default_factory=dict)
    escalated_recurrences: int = 0
    roads_with_health: int = 0
    road_health_status_counts: dict[str, int] = Field(default_factory=dict)
    repair_verification_results: dict[str, int] = Field(default_factory=dict)


class DamageTrendPoint(BaseModel):
    date: str
    count: int
    severity_breakdown: dict[str, int] = Field(default_factory=dict)


class DamageTrendsData(BaseModel):
    series: list[DamageTrendPoint]
    by_type: dict[str, int]
    by_severity: dict[str, int]
    total_damages: int


class CriticalSegmentSummary(BaseModel):
    segment_id: uuid.UUID
    road_id: uuid.UUID
    road_name: str
    segment_number: int
    current_health_score: float | None
    classification: str
    open_damages_count: int


class RoadHealthAnalyticsData(BaseModel):
    average_health: float | None
    health_distribution: dict[str, int]  # GOOD, FAIR, POOR, CRITICAL
    critical_segments: list[CriticalSegmentSummary]
    total_segments_evaluated: int
    segments_insufficient_data: int = 0


class MaintenanceAnalyticsData(BaseModel):
    open_jobs: int
    in_progress_jobs: int
    completed_jobs: int
    verified_repairs: int
    rejected_repairs: int
    verification_rate: float
    avg_completion_time_days: float | None = None
    recurrence_after_repair_count: int
    by_status: dict[str, int] = Field(default_factory=dict)
    verification_pending_jobs: int = 0


class InspectionAnalyticsData(BaseModel):
    total_inspections: int
    by_status: dict[str, int]
    total_media_captured: int
    ai_processed_count: int
