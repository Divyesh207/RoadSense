import uuid

import pytest
import pytest_asyncio
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base
from app.models.history import AuditLog
from app.models.identity import (
    Organization,
    OrganizationMembership,
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions,
)
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool


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


AUTH_TABLES = [
    Organization.__table__,
    User.__table__,
    Role.__table__,
    Permission.__table__,
    role_permissions,
    OrganizationMembership.__table__,
    RefreshToken.__table__,
    AuditLog.__table__,
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
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=AUTH_TABLES))
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=AUTH_TABLES))
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
        p_insp_create = Permission(id=uuid.uuid4(), code="inspections:create", name="Create Inspection", resource="inspections", action="create")
        p_insp_read = Permission(id=uuid.uuid4(), code="inspections:read", name="Read Inspection", resource="inspections", action="read")
        p_maint_read = Permission(id=uuid.uuid4(), code="maintenance:read", name="Read Maintenance", resource="maintenance", action="read")
        p_maint_update = Permission(id=uuid.uuid4(), code="maintenance:update", name="Update Maintenance", resource="maintenance", action="update")
        session.add_all([
            p_roads_read, p_roads_create, p_roads_update, p_roads_delete,
            p_insp_create, p_insp_read, p_maint_read, p_maint_update,
        ])

        # Role-Permission mappings
        role_auth.permissions.extend([p_roads_read, p_roads_create, p_roads_update, p_roads_delete, p_insp_read, p_maint_read])
        role_insp.permissions.extend([p_roads_read, p_insp_read, p_insp_create])
        role_crew.permissions.extend([p_roads_read, p_maint_read, p_maint_update])
        role_analyst.permissions.extend([p_roads_read, p_insp_read, p_maint_read])

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
