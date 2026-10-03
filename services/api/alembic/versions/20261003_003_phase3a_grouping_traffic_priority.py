"""phase 3a: damage observations (GPS grouping), road traffic, priority factors

Non-destructive: only adds a table, nullable columns and one column with a safe
server default, then backfills one observation per existing damage record so the
inspection -> media -> detection -> damage trail is complete for old data too.

Revision ID: 003_phase3a_foundation
Revises: 002_drop_duplicate_gist
Create Date: 2026-10-03 09:00:00.000000

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_phase3a_foundation"
down_revision: str | None = "002_drop_duplicate_gist"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # damage_records: grouping counters
    op.add_column("damage_records", sa.Column("observation_count", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("damage_records", sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint("chk_damage_observation_count_positive", "damage_records", "observation_count >= 1")
    op.execute("UPDATE damage_records SET last_observed_at = COALESCE(detected_at, created_at)")

    # damage_observations: one row per sighting
    op.create_table(
        "damage_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("damage_record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("damage_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("detection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ai_detections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inspection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True),
        sa.Column("match_method", sa.String(30), nullable=False),
        sa.Column("distance_meters", sa.Numeric(10, 3), nullable=True),
        sa.Column("location", geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("detection_id", name="uq_damage_observations_detection"),
        sa.CheckConstraint("match_method IN ('NEW_RECORD', 'GPS_GROUPED', 'MANUAL')", name="chk_damage_observation_method"),
        sa.CheckConstraint("distance_meters IS NULL OR distance_meters >= 0", name="chk_damage_observation_distance"),
    )
    op.create_index("ix_damage_observations_organization_id", "damage_observations", ["organization_id"])
    op.create_index("ix_damage_observations_damage_record_id", "damage_observations", ["damage_record_id"])
    op.create_index("ix_damage_observations_inspection_id", "damage_observations", ["inspection_id"])
    op.create_index("ix_damage_observations_media_id", "damage_observations", ["media_id"])
    op.create_index("damage_observations_location_gist", "damage_observations", ["location"], postgresql_using="gist")

    # Backfill: each existing damage record is its own first observation.
    op.execute(
        """
        INSERT INTO damage_observations
            (id, organization_id, damage_record_id, detection_id, inspection_id, media_id,
             match_method, distance_meters, location, observed_at, created_at)
        SELECT gen_random_uuid(), d.organization_id, d.id, d.source_detection_id, d.inspection_id, det.media_id,
               CASE WHEN d.source_detection_id IS NULL THEN 'MANUAL' ELSE 'NEW_RECORD' END,
               0, d.location, COALESCE(d.detected_at, d.created_at), now()
        FROM damage_records d
        LEFT JOIN ai_detections det ON det.id = d.source_detection_id
        """
    )

    # roads: documented road-level traffic (nullable = unknown)
    op.add_column("roads", sa.Column("traffic_volume_class", sa.String(20), nullable=True))
    op.add_column("roads", sa.Column("traffic_aadt", sa.Integer(), nullable=True))
    op.add_column("roads", sa.Column("traffic_data_source", sa.String(255), nullable=True))
    op.create_check_constraint(
        "chk_roads_traffic_volume_class", "roads",
        "traffic_volume_class IS NULL OR traffic_volume_class IN ('LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH')",
    )
    op.create_check_constraint("chk_roads_traffic_aadt_nonnegative", "roads", "traffic_aadt IS NULL OR traffic_aadt >= 0")

    # maintenance_jobs: explainable priority inputs/components
    op.add_column("maintenance_jobs", sa.Column("priority_factors", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("maintenance_jobs", "priority_factors")
    op.drop_constraint("chk_roads_traffic_aadt_nonnegative", "roads", type_="check")
    op.drop_constraint("chk_roads_traffic_volume_class", "roads", type_="check")
    op.drop_column("roads", "traffic_data_source")
    op.drop_column("roads", "traffic_aadt")
    op.drop_column("roads", "traffic_volume_class")
    op.drop_index("damage_observations_location_gist", table_name="damage_observations")
    op.drop_table("damage_observations")
    op.drop_constraint("chk_damage_observation_count_positive", "damage_records", type_="check")
    op.drop_column("damage_records", "last_observed_at")
    op.drop_column("damage_records", "observation_count")
