import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add services/api and services/ai-worker to Python path
ai_worker_dir = Path(__file__).resolve().parent.parent
api_dir = ai_worker_dir.parent / "api"
if str(ai_worker_dir) not in sys.path:
    sys.path.insert(0, str(ai_worker_dir))
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import geoalchemy2.admin.dialects.sqlite as ga_sqlite
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.ai import (
    AIDetection,
    AIModel,
    AIProcessingRun,
    DamageType,
)
from app.models.inspection import Inspection, InspectionMedia
from app.models.jobs import ProcessingJob
from app.models.maintenance import MaintenanceJob
from app.models.repair import RepairEvidence, RepairVerification
from app.models.road import Road, RoadSegment

# Bypass SpatiaLite DDL event triggers when testing on vanilla SQLite
ga_sqlite.after_create = lambda *args, **kwargs: None
ga_sqlite.before_create = lambda *args, **kwargs: None
ga_sqlite.before_drop = lambda *args, **kwargs: None
ga_sqlite.after_drop = lambda *args, **kwargs: None

Geometry.bind_expression = lambda self, bindvalue: bindvalue
Geometry.column_expression = lambda self, col: col

orig_result_proc = Geometry.result_processor


def custom_result_proc(self, dialect, coltype):
    if dialect.name == "sqlite":

        def process(value):
            if value is None:
                return None
            if isinstance(value, (bytes, memoryview)):
                return WKBElement(bytes(value), srid=self.srid)
            if isinstance(value, str):
                return WKTElement(value, srid=self.srid)
            return value

        return process
    return orig_result_proc(self, dialect, coltype)


Geometry.result_processor = custom_result_proc


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


@compiles(Geometry, "sqlite")
def compile_geom_sqlite(type_, compiler, **kw):
    return "TEXT"


TEST_TABLES = [
    Road.__table__,
    RoadSegment.__table__,
    Inspection.__table__,
    InspectionMedia.__table__,
    ProcessingJob.__table__,
    AIModel.__table__,
    DamageType.__table__,
    AIProcessingRun.__table__,
    AIDetection.__table__,
    MaintenanceJob.__table__,
    RepairEvidence.__table__,
    RepairVerification.__table__,
]


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def isolated_model_registry(tmp_path, monkeypatch):
    """Never pick up weights from a developer's data/models; each test starts
    with a fresh registry and no trained model unless it provides one."""
    from inference.model_registry import ModelRegistry

    monkeypatch.setenv("YOLO_MODEL_PATH", str(tmp_path / "no-weights" / "pothole_yolov8.pt"))
    monkeypatch.delenv("AI_REQUIRE_TRAINED_MODEL", raising=False)
    ModelRegistry.reset()
    yield
    ModelRegistry.reset()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=TEST_TABLES))

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=TEST_TABLES))

    await engine.dispose()
