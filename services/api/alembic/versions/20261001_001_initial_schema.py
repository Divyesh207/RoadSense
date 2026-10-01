"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-01 18:45:00.000000

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable required PostgreSQL extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 2. organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("organization_type", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("organizations_code_idx", "organizations", ["code"])

    # 3. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("CREATE UNIQUE INDEX users_email_lower_idx ON users (LOWER(email));")

    # 4. roles
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("roles_code_idx", "roles", ["code"])

    # 5. permissions
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("resource", sa.String(50), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("permissions_code_idx", "permissions", ["code"])

    # 6. role_permissions
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    # 7. organization_memberships
    op.create_table(
        "organization_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("org_membership_user_org_idx", "organization_memberships", ["user_id", "organization_id"])
    op.create_index("org_membership_org_idx", "organization_memberships", ["organization_id"])

    # 8. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("device_identifier", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("refresh_tokens_user_idx", "refresh_tokens", ["user_id"])

    # 9. roads
    op.create_table(
        "roads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("road_code", sa.String(100), nullable=True),
        sa.Column("road_type", sa.String(50), nullable=True),
        sa.Column("administrative_area", sa.String(150), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="LINESTRING", srid=4326), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("roads_organization_idx", "roads", ["organization_id"])
    op.create_index("roads_code_idx", "roads", ["road_code"])
    op.execute("CREATE INDEX roads_geometry_gist ON roads USING GIST (geometry);")

    # 10. road_segments
    op.create_table(
        "road_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("segment_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column("start_chainage", sa.Numeric(12, 3), nullable=True),
        sa.Column("end_chainage", sa.Numeric(12, 3), nullable=True),
        sa.Column("length_meters", sa.Numeric(12, 3), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="LINESTRING", srid=4326), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("road_id", "segment_number", name="uq_road_segments_road_segment_number"),
        sa.CheckConstraint("segment_number > 0", name="chk_road_segments_segment_number_positive"),
        sa.CheckConstraint("length_meters IS NULL OR length_meters >= 0", name="chk_road_segments_length_nonnegative"),
    )
    op.create_index("road_segments_organization_idx", "road_segments", ["organization_id"])
    op.create_index("road_segments_road_idx", "road_segments", ["road_id"])
    op.execute("CREATE INDEX road_segments_geometry_gist ON road_segments USING GIST (geometry);")

    # 11. inspections
    op.create_table(
        "inspections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspector_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default=sa.text("'DRAFT'")),
        sa.Column("source", sa.String(30), nullable=False, server_default=sa.text("'ANDROID'")),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("gps_accuracy_meters", sa.Numeric(10, 3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("failure_code", sa.String(100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("client_inspection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("gps_accuracy_meters IS NULL OR gps_accuracy_meters >= 0", name="chk_inspections_accuracy_nonnegative"),
    )
    op.create_index("inspections_organization_idx", "inspections", ["organization_id"])
    op.create_index("inspections_inspector_idx", "inspections", ["inspector_user_id"])
    op.create_index("inspections_road_idx", "inspections", ["road_id"])
    op.create_index("inspections_segment_idx", "inspections", ["road_segment_id"])
    op.create_index("inspections_status_idx", "inspections", ["status"])
    op.create_index("inspections_captured_at_idx", "inspections", ["captured_at"])
    op.execute("CREATE INDEX inspections_location_gist ON inspections USING GIST (location);")

    # 12. inspection_media
    op.create_table(
        "inspection_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("storage_bucket", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.Numeric(8, 3), nullable=True),
        sa.Column("upload_status", sa.String(30), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="chk_media_size_nonnegative"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="chk_media_duration_nonnegative"),
        sa.CheckConstraint("width_px IS NULL OR width_px > 0", name="chk_media_width_positive"),
        sa.CheckConstraint("height_px IS NULL OR height_px > 0", name="chk_media_height_positive"),
    )
    op.create_index("inspection_media_org_idx", "inspection_media", ["organization_id"])
    op.create_index("inspection_media_inspection_idx", "inspection_media", ["inspection_id"])

    # 13. processing_jobs
    op.create_table(
        "processing_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("worker_version", sa.String(100), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "job_type", "idempotency_key", name="uq_processing_jobs_idempotency"),
        sa.CheckConstraint("attempts >= 0", name="chk_jobs_attempts_nonnegative"),
        sa.CheckConstraint("max_attempts >= 1", name="chk_jobs_max_attempts_positive"),
        sa.CheckConstraint("priority >= 0", name="chk_jobs_priority_nonnegative"),
    )
    op.create_index("processing_jobs_org_idx", "processing_jobs", ["organization_id"])
    op.create_index("processing_jobs_status_idx", "processing_jobs", ["status"])
    op.create_index("processing_jobs_type_idx", "processing_jobs", ["job_type"])

    # 14. ai_models
    op.create_table(
        "ai_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("model_family", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=False),
        sa.Column("artifact_checksum", sa.String(128), nullable=True),
        sa.Column("dataset_version", sa.String(100), nullable=True),
        sa.Column("configuration_version", sa.String(100), nullable=True),
        sa.Column("framework", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'ACTIVE'")),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", "version", name="uq_ai_models_name_version"),
    )
    op.create_index("ai_models_status_idx", "ai_models", ["status"])
    op.create_index("ai_models_type_idx", "ai_models", ["model_type"])

    # 15. ai_processing_runs
    op.create_table(
        "ai_processing_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True),
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column("configuration_version", sa.String(100), nullable=True),
        sa.Column("confidence_threshold", sa.Numeric(6, 5), nullable=True),
        sa.Column("input_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("output_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ai_runs_org_idx", "ai_processing_runs", ["organization_id"])
    op.create_index("ai_runs_model_idx", "ai_processing_runs", ["model_id"])

    # 16. damage_types
    op.create_table(
        "damage_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("damage_types_code_idx", "damage_types", ["code"])

    # 17. ai_detections
    op.create_table(
        "ai_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_processing_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_processing_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspection_media.id", ondelete="CASCADE"), nullable=False),
        sa.Column("damage_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("frame_timestamp_ms", sa.BigInteger(), nullable=True),
        sa.Column("confidence", sa.Numeric(7, 6), nullable=False),
        sa.Column("bbox_x_min", sa.Numeric(10, 7), nullable=False),
        sa.Column("bbox_y_min", sa.Numeric(10, 7), nullable=False),
        sa.Column("bbox_x_max", sa.Numeric(10, 7), nullable=False),
        sa.Column("bbox_y_max", sa.Numeric(10, 7), nullable=False),
        sa.Column("pixel_width", sa.Integer(), nullable=True),
        sa.Column("pixel_height", sa.Integer(), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("raw_output", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="chk_detections_confidence_range"),
        sa.CheckConstraint("bbox_x_min >= 0 AND bbox_x_min <= 1", name="chk_bbox_x_min"),
        sa.CheckConstraint("bbox_y_min >= 0 AND bbox_y_min <= 1", name="chk_bbox_y_min"),
        sa.CheckConstraint("bbox_x_max >= 0 AND bbox_x_max <= 1", name="chk_bbox_x_max"),
        sa.CheckConstraint("bbox_y_max >= 0 AND bbox_y_max <= 1", name="chk_bbox_y_max"),
        sa.CheckConstraint("bbox_x_min < bbox_x_max", name="chk_bbox_x_order"),
        sa.CheckConstraint("bbox_y_min < bbox_y_max", name="chk_bbox_y_order"),
    )
    op.create_index("ai_detections_org_idx", "ai_detections", ["organization_id"])
    op.create_index("ai_detections_inspection_idx", "ai_detections", ["inspection_id"])
    op.create_index("ai_detections_media_idx", "ai_detections", ["media_id"])
    op.create_index("ai_detections_run_idx", "ai_detections", ["ai_processing_run_id"])
    op.create_index("ai_detections_damage_type_idx", "ai_detections", ["damage_type_id"])
    op.execute("CREATE INDEX ai_detections_location_gist ON ai_detections USING GIST (location);")

    # 18. damage_records
    op.create_table(
        "damage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_detection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_detections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("damage_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_types.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False, server_default=sa.text("'AI'")),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("severity_score", sa.Numeric(7, 4), nullable=True),
        sa.Column("severity_method_version", sa.String(100), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'DETECTED'")),
        sa.Column("confidence", sa.Numeric(7, 6), nullable=True),
        sa.Column("estimated_area_m2", sa.Numeric(14, 4), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="chk_damage_confidence_range"),
        sa.CheckConstraint("severity_score IS NULL OR (severity_score >= 0 AND severity_score <= 100)", name="chk_damage_severity_score_range"),
        sa.CheckConstraint("estimated_area_m2 IS NULL OR estimated_area_m2 >= 0", name="chk_damage_area_nonnegative"),
    )
    op.create_index("damage_records_org_idx", "damage_records", ["organization_id"])
    op.create_index("damage_records_segment_idx", "damage_records", ["road_segment_id"])
    op.create_index("damage_records_severity_idx", "damage_records", ["severity"])
    op.create_index("damage_records_status_idx", "damage_records", ["status"])
    op.create_index("damage_records_detected_at_idx", "damage_records", ["detected_at"])
    op.execute("CREATE INDEX damage_records_location_gist ON damage_records USING GIST (location);")

    # 19. damage_reviews
    op.create_table(
        "damage_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("damage_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("review_status", sa.String(30), nullable=False),
        sa.Column("original_damage_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_damage_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_severity", sa.String(20), nullable=True),
        sa.Column("reviewed_severity", sa.String(20), nullable=True),
        sa.Column("original_confidence", sa.Numeric(7, 6), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("damage_reviews_org_idx", "damage_reviews", ["organization_id"])
    op.create_index("damage_reviews_damage_record_idx", "damage_reviews", ["damage_record_id"])

    # 20. road_health_snapshots
    op.create_table(
        "road_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("health_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("health_status", sa.String(30), nullable=False),
        sa.Column("calculation_version", sa.String(100), nullable=False),
        sa.Column("input_data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("calculation_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("health_score IS NULL OR (health_score >= 0 AND health_score <= 100)", name="chk_health_score_range"),
    )
    op.create_index("road_health_org_idx", "road_health_snapshots", ["organization_id"])
    op.create_index("road_health_segment_idx", "road_health_snapshots", ["road_segment_id"])
    op.create_index("road_health_calculated_idx", "road_health_snapshots", ["calculated_at"])

    # 21. maintenance_priority_snapshots
    op.create_table(
        "maintenance_priority_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("priority_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("priority_level", sa.String(30), nullable=False),
        sa.Column("calculation_version", sa.String(100), nullable=False),
        sa.Column("factors", postgresql.JSONB(), nullable=False),
        sa.Column("input_data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("priority_score IS NULL OR (priority_score >= 0 AND priority_score <= 100)", name="chk_priority_score_range"),
    )
    op.create_index("priority_org_idx", "maintenance_priority_snapshots", ["organization_id"])
    op.create_index("priority_segment_idx", "maintenance_priority_snapshots", ["road_segment_id"])

    # 22. deterioration_predictions
    op.create_table(
        "deterioration_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("prediction_horizon_days", sa.Integer(), nullable=False),
        sa.Column("target_type", sa.String(60), nullable=False),
        sa.Column("predicted_value", sa.Numeric(14, 6), nullable=True),
        sa.Column("predicted_risk", sa.Numeric(6, 2), nullable=True),
        sa.Column("uncertainty_lower", sa.Numeric(14, 6), nullable=True),
        sa.Column("uncertainty_upper", sa.Numeric(14, 6), nullable=True),
        sa.Column("confidence", sa.Numeric(7, 6), nullable=True),
        sa.Column("feature_version", sa.String(100), nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("input_data_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'GENERATED'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("prediction_horizon_days > 0", name="chk_prediction_horizon_positive"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="chk_prediction_confidence_range"),
        sa.CheckConstraint("predicted_risk IS NULL OR (predicted_risk >= 0 AND predicted_risk <= 100)", name="chk_prediction_risk_range"),
    )
    op.create_index("predictions_org_idx", "deterioration_predictions", ["organization_id"])
    op.create_index("predictions_segment_idx", "deterioration_predictions", ["road_segment_id"])

    # 23. maintenance_jobs
    op.create_table(
        "maintenance_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority_level", sa.String(30), nullable=False, server_default=sa.text("'MEDIUM'")),
        sa.Column("priority_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("priority_score IS NULL OR (priority_score >= 0 AND priority_score <= 100)", name="chk_maintenance_priority_score_range"),
    )
    op.create_index("maintenance_jobs_org_idx", "maintenance_jobs", ["organization_id"])
    op.create_index("maintenance_jobs_status_idx", "maintenance_jobs", ["status"])
    op.create_index("maintenance_jobs_assigned_idx", "maintenance_jobs", ["assigned_to_user_id"])
    op.create_index("maintenance_jobs_due_idx", "maintenance_jobs", ["due_at"])
    op.execute("CREATE INDEX maintenance_jobs_location_gist ON maintenance_jobs USING GIST (location);")

    # 24. maintenance_damage_links
    op.create_table(
        "maintenance_damage_links",
        sa.Column("maintenance_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("damage_record_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_records.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relationship_type", sa.String(40), nullable=False, server_default=sa.text("'PRIMARY'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # 25. maintenance_status_history
    op.create_table(
        "maintenance_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("maintenance_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_status", sa.String(40), nullable=True),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("maintenance_status_history_job_idx", "maintenance_status_history", ["maintenance_job_id"])

    # 26. repair_evidence
    op.create_table(
        "repair_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("maintenance_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("storage_bucket", sa.String(100), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("media_type", sa.String(20), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="chk_repair_evidence_size_nonnegative"),
    )
    op.create_index("repair_evidence_org_idx", "repair_evidence", ["organization_id"])
    op.create_index("repair_evidence_job_idx", "repair_evidence", ["maintenance_job_id"])
    op.execute("CREATE INDEX repair_evidence_location_gist ON repair_evidence USING GIST (location);")

    # 27. repair_verifications
    op.create_table(
        "repair_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("maintenance_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ai_processing_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ai_processing_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("ai_confidence", sa.Numeric(7, 6), nullable=True),
        sa.Column("comparison_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("findings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)", name="chk_verification_confidence_range"),
    )
    op.create_index("repair_verifications_org_idx", "repair_verifications", ["organization_id"])
    op.create_index("repair_verifications_job_idx", "repair_verifications", ["maintenance_job_id"])

    # 28. recurrence_records
    op.create_table(
        "recurrence_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("historical_damage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("new_damage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("damage_records.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("related_maintenance_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("maintenance_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_repair_verification_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repair_verifications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("road_segment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("spatial_distance_meters", sa.Numeric(12, 3), nullable=True),
        sa.Column("temporal_distance_days", sa.Integer(), nullable=True),
        sa.Column("similarity_score", sa.Numeric(7, 6), nullable=True),
        sa.Column("recurrence_score", sa.Numeric(7, 6), nullable=True),
        sa.Column("detection_method_version", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'POTENTIAL'")),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("spatial_distance_meters IS NULL OR spatial_distance_meters >= 0", name="chk_recurrence_distance_nonnegative"),
        sa.CheckConstraint("similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1)", name="chk_recurrence_similarity_range"),
        sa.CheckConstraint("recurrence_score IS NULL OR (recurrence_score >= 0 AND recurrence_score <= 1)", name="chk_recurrence_score_range"),
    )
    op.create_index("recurrence_records_org_idx", "recurrence_records", ["organization_id"])
    op.create_index("recurrence_records_segment_idx", "recurrence_records", ["road_segment_id"])

    # 29. notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notification_type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("notifications_user_idx", "notifications", ["user_id"])
    op.create_index("notifications_unread_idx", "notifications", ["user_id", "read_at"])
    op.create_index("notifications_created_at_idx", "notifications", ["created_at"])

    # 30. generated_reports
    op.create_table(
        "generated_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("report_type", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'QUEUED'")),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("storage_bucket", sa.String(100), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("processing_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("reports_org_idx", "generated_reports", ["organization_id"])

    # 31. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("before_data", postgresql.JSONB(), nullable=True),
        sa.Column("after_data", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("audit_logs_created_idx", "audit_logs", ["created_at"])
    op.create_index("audit_logs_action_entity_idx", "audit_logs", ["action", "entity_type"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("audit_logs")
    op.drop_table("generated_reports")
    op.drop_table("notifications")
    op.drop_table("recurrence_records")
    op.drop_table("repair_verifications")
    op.drop_table("repair_evidence")
    op.drop_table("maintenance_status_history")
    op.drop_table("maintenance_damage_links")
    op.drop_table("maintenance_jobs")
    op.drop_table("deterioration_predictions")
    op.drop_table("maintenance_priority_snapshots")
    op.drop_table("road_health_snapshots")
    op.drop_table("damage_reviews")
    op.drop_table("damage_records")
    op.drop_table("ai_detections")
    op.drop_table("damage_types")
    op.drop_table("ai_processing_runs")
    op.drop_table("ai_models")
    op.drop_table("processing_jobs")
    op.drop_table("inspection_media")
    op.drop_table("inspections")
    op.drop_table("road_segments")
    op.drop_table("roads")
    op.drop_table("refresh_tokens")
    op.drop_table("organization_memberships")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("organizations")
