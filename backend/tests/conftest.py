"""Shared pytest fixtures — async SQLite engine, session override, auth helpers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User

# ---------------------------------------------------------------------------
# Make PostgreSQL JSONB compile as JSON on SQLite
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler


def _visit_JSONB(self, type_, **kw):  # noqa: N802
    return "JSON"


SQLiteTypeCompiler.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Make PostgreSQL UUID work with SQLite (string bind params)
# ---------------------------------------------------------------------------

import uuid as _uuid_mod

from sqlalchemy.dialects.postgresql import UUID as PG_UUID

_orig_bind_processor = PG_UUID.bind_processor


def _patched_bind_processor(self, dialect):
    if dialect.name == "sqlite":

        def process(value):
            if value is not None:
                if isinstance(value, _uuid_mod.UUID):
                    return str(value)
                return str(value)
            return value

        return process
    return _orig_bind_processor(self, dialect)


def _patched_result_processor(self, dialect, coltype):
    if dialect.name == "sqlite":

        def process(value):
            if value is not None:
                if not isinstance(value, _uuid_mod.UUID):
                    return _uuid_mod.UUID(str(value))
                return value
            return value

        return process
    return None


PG_UUID.bind_processor = _patched_bind_processor  # type: ignore[assignment]
PG_UUID.result_processor = _patched_result_processor  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Async SQLite engine shared by every test session
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """Enable WAL + FK constraints on every raw connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# DB lifecycle — drop + create tables before each test for isolation
# ---------------------------------------------------------------------------

# Import every model so Base.metadata is fully populated
import app.models.persona  # noqa: F401
import app.models.user  # noqa: F401
import app.models.policy  # noqa: F401
import app.models.interview  # noqa: F401
import app.models.testing  # noqa: F401
import app.models.agent_config  # noqa: F401
import app.models.extension  # noqa: F401
import app.models.production  # noqa: F401


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Fresh tables for every test — full isolation without savepoints."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# FastAPI app with overridden get_db
# ---------------------------------------------------------------------------


@pytest.fixture
async def app(db: AsyncSession):
    """Return the FastAPI app with get_db overridden to use the test session."""
    from app.main import create_app

    application = create_app()

    # Disable rate limiting in tests
    application.state.limiter.enabled = False

    async def _override_get_db():
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    application.dependency_overrides[get_db] = _override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def _make_token(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id), "email": user.email, "admin": user.is_admin}
    )


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create and persist an admin user."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("admin123"),
        is_admin=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def regular_user(db: AsyncSession) -> User:
    """Create and persist a regular (non-admin) user."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        hashed_password=hash_password("user123"),
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
async def other_user(db: AsyncSession) -> User:
    """A second regular user — useful for ownership isolation tests."""
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        hashed_password=hash_password("other123"),
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(admin_user)}"}


@pytest.fixture
def user_headers(regular_user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(regular_user)}"}


@pytest.fixture
def other_headers(other_user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_token(other_user)}"}
