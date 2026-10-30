"""
Aegis Database Connection & Session Management
Supports Async SQLAlchemy over PostgreSQL (asyncpg) with automatic fallback to SQLite (aiosqlite)
for environments where PostgreSQL is not running locally.
"""

import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

Base = declarative_base()

POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://aegis_admin:aegis_secure_password@localhost:5432/aegis_fraud_db"
)
SQLITE_URL = f"sqlite+aiosqlite:///{os.path.abspath('data/aegis.db')}"

# Determine initial database engine
_active_engine = None
_session_maker = None
_is_sqlite = False


async def get_engine():
    global _active_engine, _session_maker, _is_sqlite
    if _active_engine is not None:
        return _active_engine

    # Try connecting to PostgreSQL first
    try:
        engine = create_async_engine(
            POSTGRES_URL,
            echo=False,
            pool_size=20,
            max_overflow=10,
            pool_timeout=3
        )
        # Test connection
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        print(f"[Aegis Database] Connected successfully to PostgreSQL at {POSTGRES_URL.split('@')[-1]}")
        _active_engine = engine
        _is_sqlite = False
    except Exception as e:
        print(f"[Aegis Database] PostgreSQL unavailable ({e}). Initializing SQLite fallback ({SQLITE_URL})...")
        os.makedirs("data", exist_ok=True)
        _active_engine = create_async_engine(SQLITE_URL, echo=False)
        _is_sqlite = True

    _session_maker = async_sessionmaker(_active_engine, expire_on_commit=False, class_=AsyncSession)
    return _active_engine


async def init_db():
    """Initializes schema tables if they do not exist."""
    engine = await get_engine()
    from services.api.models import db_models  # Ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"[Aegis Database] Tables initialized (Mode: {'SQLite' if _is_sqlite else 'PostgreSQL'}).")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for FastAPI route endpoints."""
    await get_engine()
    async with _session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
