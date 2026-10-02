from geoalchemy2 import Geometry

from app.models import (
    AIDetection,
    AIProcessingRun,
    Base,
    DamageRecord,
    DamageReview,
    DeteriorationPrediction,
    GeneratedReport,
    Inspection,
    InspectionMedia,
    MaintenanceJob,
    MaintenancePrioritySnapshot,
    MaintenanceStatusHistory,
    Notification,
    Organization,
    OrganizationMembership,
    ProcessingJob,
    RecurrenceRecord,
    RepairEvidence,
    RepairVerification,
    Road,
    RoadHealthSnapshot,
    RoadSegment,
)


def test_table_inventory():
    """Verify that all 30 authoritative tables defined in 06_DATABASE_SCHEMA.md exist in metadata."""
    expected_tables = {
        "organizations",
        "users",
        "roles",
        "permissions",
        "role_permissions",
        "organization_memberships",
        "refresh_tokens",
        "roads",
        "road_segments",
        "inspections",
        "inspection_media",
        "processing_jobs",
        "ai_models",
        "ai_processing_runs",
        "damage_types",
        "ai_detections",
        "damage_records",
        "damage_reviews",
        "road_health_snapshots",
        "maintenance_priority_snapshots",
        "deterioration_predictions",
        "maintenance_jobs",
        "maintenance_damage_links",
        "maintenance_status_history",
        "repair_evidence",
        "repair_verifications",
        "recurrence_records",
        "notifications",
        "generated_reports",
        "audit_logs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_organization_scoping():
    """Verify INV-DB-009: every tenant-owned table must include an organization_id column."""
    tenant_tables = [
        OrganizationMembership,
        Road,
        RoadSegment,
        Inspection,
        InspectionMedia,
        ProcessingJob,
        AIProcessingRun,
        AIDetection,
        DamageRecord,
        DamageReview,
        RoadHealthSnapshot,
        MaintenancePrioritySnapshot,
        DeteriorationPrediction,
        MaintenanceJob,
        MaintenanceStatusHistory,
        RepairEvidence,
        RepairVerification,
        RecurrenceRecord,
        Notification,
        GeneratedReport,
    ]

    for model in tenant_tables:
        table_name = model.__tablename__
        assert hasattr(model, "organization_id"), f"{table_name} missing organization_id column"
        col = model.__table__.c.organization_id
        assert col.nullable is False, f"{table_name}.organization_id must not be nullable"


def test_spatial_columns_and_srid():
    """Verify that PostGIS spatial columns are defined with SRID 4326."""
    spatial_checks = [
        (Road, "geometry", "LINESTRING"),
        (RoadSegment, "geometry", "LINESTRING"),
        (Inspection, "location", "POINT"),
        (InspectionMedia, "location", "POINT"),
        (AIDetection, "location", "POINT"),
        (DamageRecord, "location", "POINT"),
        (MaintenanceJob, "location", "POINT"),
        (RepairEvidence, "location", "POINT"),
    ]

    for model, col_name, geom_type in spatial_checks:
        col = getattr(model, col_name)
        assert isinstance(col.type, Geometry), f"{model.__tablename__}.{col_name} is not a Geometry type"
        assert col.type.srid == 4326, f"{model.__tablename__}.{col_name} SRID is {col.type.srid}, expected 4326"
        assert col.type.geometry_type.upper() == geom_type, f"{model.__tablename__}.{col_name} geom_type is {col.type.geometry_type}, expected {geom_type}"


def test_check_constraints():
    """Verify critical check constraints from 06_DATABASE_SCHEMA.md."""
    # road_segments
    rs_constraints = {c.name for c in RoadSegment.__table__.constraints}
    assert "chk_road_segments_segment_number_positive" in rs_constraints
    assert "chk_road_segments_length_nonnegative" in rs_constraints

    # inspections
    insp_constraints = {c.name for c in Inspection.__table__.constraints}
    assert "chk_inspections_accuracy_nonnegative" in insp_constraints

    # ai_detections
    det_constraints = {c.name for c in AIDetection.__table__.constraints}
    assert "chk_detections_confidence_range" in det_constraints
    assert "chk_bbox_x_min" in det_constraints
    assert "chk_bbox_x_max" in det_constraints
    assert "chk_bbox_x_order" in det_constraints

    # damage_records
    dmg_constraints = {c.name for c in DamageRecord.__table__.constraints}
    assert "chk_damage_confidence_range" in dmg_constraints
    assert "chk_damage_severity_score_range" in dmg_constraints
    assert "chk_damage_area_nonnegative" in dmg_constraints

    # road_health_snapshots
    health_constraints = {c.name for c in RoadHealthSnapshot.__table__.constraints}
    assert "chk_health_score_range" in health_constraints

    # deterioration_predictions
    pred_constraints = {c.name for c in DeteriorationPrediction.__table__.constraints}
    assert "chk_prediction_horizon_positive" in pred_constraints
    assert "chk_prediction_confidence_range" in pred_constraints


def test_model_relationships():
    """Verify ORM relationships are bidirectional and properly wired."""
    assert hasattr(Organization, "memberships")
    assert hasattr(Organization, "roads")
    assert hasattr(Organization, "inspections")
    assert hasattr(Road, "segments")
    assert hasattr(RoadSegment, "road")
    assert hasattr(Inspection, "media")
    assert hasattr(InspectionMedia, "inspection")
    assert hasattr(AIDetection, "processing_run")
    assert hasattr(DamageRecord, "reviews")
    assert hasattr(DamageReview, "damage_record")
    assert hasattr(MaintenanceJob, "damage_links")
    assert hasattr(MaintenanceJob, "evidence")
    assert hasattr(MaintenanceJob, "verifications")
