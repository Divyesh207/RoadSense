import uuid

import geoalchemy2.admin.dialects.sqlite as ga_sqlite
import pytest
import pytest_asyncio
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.ai import AIDetection, AIModel, AIProcessingRun, DamageType
from app.models.damage import DamageRecord, DamageReview
from app.models.history import AuditLog, RecurrenceRecord
from app.models.identity import (
    Organization,
    OrganizationMembership,
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions,
)
from app.models.inspection import Inspection, InspectionMedia
from app.models.intelligence import DeteriorationPrediction, RoadHealthSnapshot
from app.models.jobs import ProcessingJob
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.repair import RepairEvidence, RepairVerification
from app.models.road import Road, RoadSegment
from fastapi.testclient import TestClient
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement, WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

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


# Custom type compilation for SQLite in-memory test environment
@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "VARCHAR(36)"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@compiles(INET, "sqlite")
def compile_inet_sqlite(type_, compiler, **kw):
    return "VARCHAR(45)"


@compiles(Geometry, "sqlite")
def compile_geom_sqlite(type_, compiler, **kw):
    return "TEXT"


TEST_TABLES = [
    Organization.__table__,
    User.__table__,
    Role.__table__,
    Permission.__table__,
    role_permissions,
    OrganizationMembership.__table__,
    RefreshToken.__table__,
    AuditLog.__table__,
    Road.__table__,
    RoadSegment.__table__,
    Inspection.__table__,
    InspectionMedia.__table__,
    ProcessingJob.__table__,
    AIModel.__table__,
    DamageType.__table__,
    AIProcessingRun.__table__,
    AIDetection.__table__,
    DamageRecord.__table__,
    DamageReview.__table__,
    RoadHealthSnapshot.__table__,
    RecurrenceRecord.__table__,
    DeteriorationPrediction.__table__,
    MaintenanceJob.__table__,
    MaintenanceDamageLink.__table__,
    MaintenanceStatusHistory.__table__,
    RepairEvidence.__table__,
    RepairVerification.__table__,
]

ORG_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
ORG_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

ADMIN_USER_ID = uuid.UUID("a1111111-1111-1111-1111-111111111111")
AUTHORITY_USER_ID = uuid.UUID("a2222222-2222-2222-2222-222222222222")
INSPECTOR_USER_ID = uuid.UUID("a3333333-3333-3333-3333-333333333333")
CREW_USER_ID = uuid.UUID("a4444444-4444-4444-4444-444444444444")
INACTIVE_USER_ID = uuid.UUID("a5555555-5555-5555-5555-555555555555")
OTHER_ORG_USER_ID = uuid.UUID("a6666666-6666-6666-6666-666666666666")


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=TEST_TABLES))
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=TEST_TABLES))
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        # Seed test organizations
        org1 = Organization(
            id=ORG_1_ID,
            name="Primary State Road Authority",
            code="PSRA-01",
            organization_type="STATE_HIGHWAY",
            is_active=True,
        )
        org2 = Organization(
            id=ORG_2_ID,
            name="Secondary Municipal Corporation",
            code="SMC-02",
            organization_type="MUNICIPAL",
            is_active=True,
        )
        session.add_all([org1, org2])

        # Seed roles
        role_admin = Role(id=uuid.uuid4(), code="ADMINISTRATOR", name="Administrator", is_system_role=True)
        role_auth = Role(id=uuid.uuid4(), code="ROAD_AUTHORITY", name="Road Authority", is_system_role=True)
        role_insp = Role(id=uuid.uuid4(), code="FIELD_INSPECTOR", name="Field Inspector", is_system_role=True)
        role_crew = Role(id=uuid.uuid4(), code="MAINTENANCE_CREW", name="Maintenance Crew", is_system_role=True)
        role_analyst = Role(id=uuid.uuid4(), code="ANALYST", name="Analyst", is_system_role=True)
        session.add_all([role_admin, role_auth, role_insp, role_crew, role_analyst])

        # Seed permissions
        p_roads_read = Permission(id=uuid.uuid4(), code="roads:read", name="Read Roads", resource="roads", action="read")
        p_roads_create = Permission(id=uuid.uuid4(), code="roads:create", name="Create Roads", resource="roads", action="create")
        p_roads_update = Permission(id=uuid.uuid4(), code="roads:update", name="Update Roads", resource="roads", action="update")
        p_roads_delete = Permission(id=uuid.uuid4(), code="roads:delete", name="Delete Roads", resource="roads", action="delete")

        p_segs_read = Permission(id=uuid.uuid4(), code="road_segments:read", name="Read Road Segments", resource="road_segments", action="read")
        p_segs_create = Permission(id=uuid.uuid4(), code="road_segments:create", name="Create Road Segments", resource="road_segments", action="create")
        p_segs_update = Permission(id=uuid.uuid4(), code="road_segments:update", name="Update Road Segments", resource="road_segments", action="update")
        p_segs_delete = Permission(id=uuid.uuid4(), code="road_segments:delete", name="Delete Road Segments", resource="road_segments", action="delete")

        p_insp_create = Permission(id=uuid.uuid4(), code="inspections:create", name="Create Inspection", resource="inspections", action="create")
        p_insp_read = Permission(id=uuid.uuid4(), code="inspections:read", name="Read Inspection", resource="inspections", action="read")
        p_insp_update = Permission(id=uuid.uuid4(), code="inspections:update", name="Update Inspection", resource="inspections", action="update")
        p_insp_submit = Permission(id=uuid.uuid4(), code="inspections:submit", name="Submit Inspection", resource="inspections", action="submit")
        p_insp_process = Permission(id=uuid.uuid4(), code="inspections:process", name="Process Inspection", resource="inspections", action="process")
        p_media_read = Permission(id=uuid.uuid4(), code="inspection_media:read", name="Read Media", resource="inspection_media", action="read")

        p_maint_read = Permission(id=uuid.uuid4(), code="maintenance:read", name="Read Maintenance", resource="maintenance", action="read")
        p_maint_create = Permission(id=uuid.uuid4(), code="maintenance:create", name="Create Maintenance", resource="maintenance", action="create")
        p_maint_update = Permission(id=uuid.uuid4(), code="maintenance:update", name="Update Maintenance", resource="maintenance", action="update")
        p_maint_assign = Permission(id=uuid.uuid4(), code="maintenance:assign", name="Assign Maintenance", resource="maintenance", action="assign")
        p_maint_status = Permission(id=uuid.uuid4(), code="maintenance:status_update", name="Update Maintenance Status", resource="maintenance", action="status_update")
        p_maint_link = Permission(id=uuid.uuid4(), code="maintenance:link_damage", name="Link Maintenance Damage", resource="maintenance", action="link_damage")
        p_maint_history = Permission(id=uuid.uuid4(), code="maintenance:view_history", name="View Maintenance History", resource="maintenance", action="view_history")
        p_maint_verify = Permission(id=uuid.uuid4(), code="maintenance:verify", name="Verify Maintenance", resource="maintenance", action="verify")

        p_dmg_read = Permission(id=uuid.uuid4(), code="damage_records:read", name="Read Damage", resource="damage_records", action="read")
        p_dmg_create = Permission(id=uuid.uuid4(), code="damage_records:create", name="Create Damage", resource="damage_records", action="create")
        p_dmg_update = Permission(id=uuid.uuid4(), code="damage_records:update", name="Update Damage", resource="damage_records", action="update")
        p_dmg_review = Permission(id=uuid.uuid4(), code="damage_records:review", name="Review Damage", resource="damage_records", action="review")

        p_health_read = Permission(id=uuid.uuid4(), code="road_health:read", name="Read Road Health", resource="road_health", action="read")
        p_health_calc = Permission(id=uuid.uuid4(), code="road_health:calculate", name="Calculate Road Health", resource="road_health", action="calculate")

        p_pred_read = Permission(id=uuid.uuid4(), code="predictions:read", name="Read Predictions", resource="predictions", action="read")
        p_pred_create = Permission(id=uuid.uuid4(), code="predictions:create", name="Create Predictions", resource="predictions", action="create")
        p_pred_manage = Permission(id=uuid.uuid4(), code="predictions:manage", name="Manage Predictions", resource="predictions", action="manage")

        session.add_all([
            p_roads_read, p_roads_create, p_roads_update, p_roads_delete,
            p_segs_read, p_segs_create, p_segs_update, p_segs_delete,
            p_insp_create, p_insp_read, p_insp_update, p_insp_submit, p_insp_process, p_media_read,
            p_maint_read, p_maint_create, p_maint_update, p_maint_assign, p_maint_status, p_maint_link, p_maint_history, p_maint_verify,
            p_dmg_read, p_dmg_create, p_dmg_update, p_dmg_review,
            p_health_read, p_health_calc,
            p_pred_read, p_pred_create, p_pred_manage,
        ])

        # Role-Permission mappings
        role_auth.permissions.extend([
            p_roads_read, p_roads_create, p_roads_update, p_roads_delete,
            p_segs_read, p_segs_create, p_segs_update, p_segs_delete,
            p_insp_create, p_insp_read, p_insp_update, p_insp_submit, p_insp_process, p_media_read,
            p_maint_read, p_maint_create, p_maint_update, p_maint_assign, p_maint_status, p_maint_link, p_maint_history, p_maint_verify,
            p_dmg_read, p_dmg_create, p_dmg_update, p_dmg_review,
            p_health_read, p_health_calc,
            p_pred_read, p_pred_create, p_pred_manage,
        ])
        role_insp.permissions.extend([
            p_roads_read, p_segs_read,
            p_insp_create, p_insp_read, p_insp_update, p_insp_submit, p_media_read,
            p_dmg_read, p_dmg_create,
            p_health_read,
            p_pred_read,
            p_maint_read, p_maint_history,
        ])
        role_crew.permissions.extend([
            p_roads_read, p_segs_read,
            p_maint_read, p_maint_update, p_maint_status, p_maint_link, p_maint_history,
            p_dmg_read, p_health_read,
        ])
        role_analyst.permissions.extend([p_roads_read, p_segs_read, p_insp_read, p_maint_read, p_dmg_read, p_health_read])

        # Seed initial damage types
        dt_pothole = DamageType(id=uuid.uuid4(), code="POTHOLE", name="Pothole", description="Road surface cavity", is_active=True)
        dt_crack = DamageType(id=uuid.uuid4(), code="CRACK", name="Surface Crack", description="Linear fracture", is_active=True)
        dt_dep = DamageType(id=uuid.uuid4(), code="DEPRESSION", name="Depression", description="Sunken road surface", is_active=True)
        dt_water = DamageType(id=uuid.uuid4(), code="WATERLOGGING", name="Waterlogging", description="Standing water accumulation", is_active=True)
        dt_surf = DamageType(id=uuid.uuid4(), code="SURFACE_DAMAGE", name="Surface Damage", description="Loss of aggregate", is_active=True)
        dt_other = DamageType(id=uuid.uuid4(), code="OTHER", name="Other Damage", description="Unclassified road defect", is_active=True)
        session.add_all([dt_pothole, dt_crack, dt_dep, dt_water, dt_surf, dt_other])

        # Seed users
        admin_user = User(
            id=ADMIN_USER_ID,
            email="admin@example.com",
            password_hash=hash_password("AdminSecret123!"),
            full_name="System Admin",
            is_active=True,
        )
        authority_user = User(
            id=AUTHORITY_USER_ID,
            email="authority@example.com",
            password_hash=hash_password("AuthoritySecret123!"),
            full_name="Authority Officer",
            is_active=True,
        )
        inspector_user = User(
            id=INSPECTOR_USER_ID,
            email="inspector@example.com",
            password_hash=hash_password("InspectorSecret123!"),
            full_name="Field Officer",
            is_active=True,
        )
        crew_user = User(
            id=CREW_USER_ID,
            email="crew@example.com",
            password_hash=hash_password("CrewSecret123!"),
            full_name="Maintenance Lead",
            is_active=True,
        )
        inactive_user = User(
            id=INACTIVE_USER_ID,
            email="inactive@example.com",
            password_hash=hash_password("InactiveSecret123!"),
            full_name="Inactive Officer",
            is_active=False,
        )
        other_user = User(
            id=OTHER_ORG_USER_ID,
            email="other@example.com",
            password_hash=hash_password("OtherSecret123!"),
            full_name="Other Org Officer",
            is_active=True,
        )
        session.add_all([admin_user, authority_user, inspector_user, crew_user, inactive_user, other_user])

        # Seed memberships
        m_admin = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_1_ID,
            user_id=ADMIN_USER_ID,
            role_id=role_admin.id,
            status="ACTIVE",
        )
        m_auth = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_1_ID,
            user_id=AUTHORITY_USER_ID,
            role_id=role_auth.id,
            status="ACTIVE",
        )
        m_insp = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_1_ID,
            user_id=INSPECTOR_USER_ID,
            role_id=role_insp.id,
            status="ACTIVE",
        )
        m_crew = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_1_ID,
            user_id=CREW_USER_ID,
            role_id=role_crew.id,
            status="ACTIVE",
        )
        m_inactive = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_1_ID,
            user_id=INACTIVE_USER_ID,
            role_id=role_insp.id,
            status="ACTIVE",
        )
        m_other = OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=ORG_2_ID,
            user_id=OTHER_ORG_USER_ID,
            role_id=role_insp.id,
            status="ACTIVE",
        )
        session.add_all([m_admin, m_auth, m_insp, m_crew, m_inactive, m_other])

        await session.commit()
        yield session


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
