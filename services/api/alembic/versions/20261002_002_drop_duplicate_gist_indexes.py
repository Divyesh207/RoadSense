"""drop duplicate GIST indexes

001_initial_schema created two identical GIST indexes on seven geometry
columns: the explicit `<table>_<column>_gist` index declared by the models and
the implicit `idx_<table>_<column>` index GeoAlchemy2 adds for every Geometry
column (spatial_index=True default). The models now set spatial_index=False
on those columns; this drops the implicit duplicates so each column keeps one
GIST index. inspection_media.location only ever had the implicit index and
keeps it.

Revision ID: 002_drop_duplicate_gist
Revises: 001_initial_schema
Create Date: 2026-10-02 03:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "002_drop_duplicate_gist"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DUPLICATES = [
    ("idx_roads_geometry", "roads", "geometry"),
    ("idx_road_segments_geometry", "road_segments", "geometry"),
    ("idx_inspections_location", "inspections", "location"),
    ("idx_ai_detections_location", "ai_detections", "location"),
    ("idx_damage_records_location", "damage_records", "location"),
    ("idx_maintenance_jobs_location", "maintenance_jobs", "location"),
    ("idx_repair_evidence_location", "repair_evidence", "location"),
]


def upgrade() -> None:
    for index_name, _table, _column in DUPLICATES:
        op.execute(f"DROP INDEX IF EXISTS {index_name};")


def downgrade() -> None:
    for index_name, table, column in DUPLICATES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} USING GIST ({column});")
