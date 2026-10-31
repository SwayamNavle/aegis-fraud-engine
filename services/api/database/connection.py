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
    """Initializes schema tables if they do not exist and applies non-destructive column migrations."""
    engine = await get_engine()
    from services.api.models import db_models  # Ensure models are imported
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # SQLite automated column migration helper
        if _is_sqlite:
            from sqlalchemy import text
            # Ensure predictions columns
            pred_cols = [row[1] for row in (await conn.execute(text("PRAGMA table_info(predictions)"))).fetchall()]
            if "correlation_id" not in pred_cols:
                await conn.execute(text("ALTER TABLE predictions ADD COLUMN correlation_id VARCHAR(64)"))
            if "business_decision" not in pred_cols:
                await conn.execute(text("ALTER TABLE predictions ADD COLUMN business_decision VARCHAR(32) DEFAULT 'APPROVE'"))
            if "ground_truth" not in pred_cols:
                await conn.execute(text("ALTER TABLE predictions ADD COLUMN ground_truth VARCHAR(32) DEFAULT 'UNVERIFIED'"))

            # Ensure fraud_alerts columns
            alert_cols = [row[1] for row in (await conn.execute(text("PRAGMA table_info(fraud_alerts)"))).fetchall()]
            if "reviewer" not in alert_cols:
                await conn.execute(text("ALTER TABLE fraud_alerts ADD COLUMN reviewer VARCHAR(64)"))
            if "notes" not in alert_cols:
                await conn.execute(text("ALTER TABLE fraud_alerts ADD COLUMN notes VARCHAR(512)"))
            if "final_ground_truth" not in alert_cols:
                await conn.execute(text("ALTER TABLE fraud_alerts ADD COLUMN final_ground_truth VARCHAR(32) DEFAULT 'UNVERIFIED'"))

            # Ensure model_versions columns
            mv_cols = [row[1] for row in (await conn.execute(text("PRAGMA table_info(model_versions)"))).fetchall()]
            if "dataset_version" not in mv_cols:
                await conn.execute(text("ALTER TABLE model_versions ADD COLUMN dataset_version VARCHAR(32) DEFAULT 'v1.0'"))
            if "feature_version" not in mv_cols:
                await conn.execute(text("ALTER TABLE model_versions ADD COLUMN feature_version VARCHAR(32) DEFAULT 'v1.0'"))
            if "status" not in mv_cols:
                await conn.execute(text("ALTER TABLE model_versions ADD COLUMN status VARCHAR(32) DEFAULT 'PRODUCTION'"))
            if "updated_at" not in mv_cols:
                await conn.execute(text("ALTER TABLE model_versions ADD COLUMN updated_at TIMESTAMP"))

    print(f"[Aegis Database] Tables initialized (Mode: {'SQLite' if _is_sqlite else 'PostgreSQL'}).")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency provider for FastAPI route endpoints."""
    await get_engine()
    async with _session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
