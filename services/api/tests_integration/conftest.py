"""
Real PostgreSQL 16 + PostGIS 3.4 integration fixtures.

Run separately from the SQLite unit suite (tests/conftest.py monkeypatches
GeoAlchemy2 globally for SQLite, which must not leak into these tests):

    POSTGIS_TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/road_platform_it \
        python -m pytest tests_integration

The database named in the URL is DROPPED and recreated, then migrated with
`alembic upgrade head`. Never point this at a database you care about.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio

PG_URL = os.getenv("POSTGIS_TEST_DATABASE_URL", "")
API_DIR = Path(__file__).resolve().parent.parent

if PG_URL:
    # Must be in place before app settings are imported.
    os.environ["DATABASE_URL"] = PG_URL
    os.environ["DATABASE_URL_SYNC"] = PG_URL.replace("+asyncpg", "")
    os.environ.setdefault("DEBUG", "false")


def pytest_collection_modifyitems(config, items):
    if PG_URL:
        return
    # Collection hooks are session-wide: only touch this directory's tests.
    here = Path(__file__).resolve().parent
    skip = pytest.mark.skip(reason="POSTGIS_TEST_DATABASE_URL not set; real PostGIS integration tests skipped")
    for item in items:
        if here in Path(str(item.path)).resolve().parents:
            item.add_marker(skip)


def _recreate_database() -> None:
    import psycopg2

    parsed = urlparse(PG_URL.replace("+asyncpg", ""))
    db_name = parsed.path.lstrip("/")
    if not db_name or db_name in ("postgres", "road_platform"):
        raise RuntimeError(f"Refusing to drop database '{db_name}'; use a dedicated test database.")
    conn = psycopg2.connect(
        host=parsed.hostname, port=parsed.port or 5432, user=parsed.username, password=parsed.password, dbname="postgres"
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)')
        cur.execute(f'CREATE DATABASE "{db_name}"')
    conn.close()


@pytest.fixture(scope="session")
def migrated_database() -> str:
    from geoalchemy2 import Geometry

    if getattr(Geometry.bind_expression, "__name__", "") == "<lambda>":
        pytest.fail("GeoAlchemy2 is patched by tests/conftest.py; run tests_integration in a separate pytest invocation.")
    _recreate_database()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_DIR,
        env={**os.environ},
        check=True,
        capture_output=True,
    )
    return PG_URL


ALL_PERMISSIONS = [
    "roads:create", "roads:read", "roads:update", "roads:delete",
    "road_segments:create", "road_segments:read", "road_segments:update", "road_segments:delete",
    "inspections:create", "inspections:read", "inspections:update", "inspections:submit", "inspections:process",
    "inspection_media:read", "damage_records:read",
]
ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_EMAIL = "it-authority@example.com"
USER_PASSWORD = "IntegrationSecret123!"


@pytest_asyncio.fixture
async def pg_engine(migrated_database):
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(migrated_database, poolclass=NullPool)
    async with engine.begin() as conn:
        tables = (
            await conn.execute(
                text(
                    "SELECT string_agg(quote_ident(tablename), ', ') FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename NOT IN ('alembic_version', 'spatial_ref_sys')"
                )
            )
        ).scalar_one()
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(pg_engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.core.security import hash_password
    from app.models.identity import (
        Organization,
        OrganizationMembership,
        Permission,
        Role,
        User,
    )

    factory = async_sessionmaker(bind=pg_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        perms = [
            Permission(id=uuid.uuid4(), code=c, name=c, resource=c.split(":")[0], action=c.split(":")[1])
            for c in ALL_PERMISSIONS
        ]
        role = Role(id=uuid.uuid4(), code="ROAD_AUTHORITY", name="Road Authority", is_system_role=True)
        role.permissions = perms
        user = User(
            id=uuid.uuid4(), email=USER_EMAIL, password_hash=hash_password(USER_PASSWORD),
            full_name="Integration Authority", is_active=True,
        )
        org = Organization(id=ORG_ID, name="Integration Org", code="IT-01", organization_type="MUNICIPAL", is_active=True)
        session.add_all([org, role, *perms, user])
        await session.flush()
        session.add(
            OrganizationMembership(id=uuid.uuid4(), organization_id=ORG_ID, user_id=user.id, role_id=role.id, status="ACTIVE")
        )
        await session.commit()
    return factory


@pytest.fixture
def local_storage(tmp_path, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "LOCAL_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", "http://it/api/v1")
    return tmp_path / "storage"


@pytest_asyncio.fixture
async def api_client(session_factory, local_storage):
    from httpx import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://it") as client:
        login = await client.post("/api/v1/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
        assert login.status_code == 200, login.text
        client.headers.update(
            {"Authorization": f"Bearer {login.json()['data']['access_token']}", "X-Organization-ID": str(ORG_ID)}
        )
        yield client
    app.dependency_overrides.clear()
