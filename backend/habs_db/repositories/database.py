"""
HABS — Async Database Engine & Session
SQLAlchemy 2.x AsyncSession with FastAPI dependency injection.
All DB calls must go through get_db() — never instantiate sessions manually.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from habs_db.settings import Settings

logger = logging.getLogger(__name__)

# ─────────────────────────────── Engine ──────────────────────────────────────

def build_engine(settings: Settings) -> AsyncEngine:
    """
    Factory that creates the async engine.
    Uses NullPool in test mode to avoid connection leaks between test cases.
    """
    pool_cls = NullPool if settings.TESTING else None

    engine_kwargs: dict = dict(
        echo=settings.DB_ECHO,
        pool_pre_ping=True,          # evicts stale connections
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )
    if pool_cls:
        engine_kwargs = dict(echo=settings.DB_ECHO, poolclass=pool_cls)

    return create_async_engine(settings.ASYNC_DATABASE_URL, **engine_kwargs)


# ─────────────────────────────── Session factory ─────────────────────────────

def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,   # prevent lazy-load errors after commit in async context
        autoflush=False,
        autocommit=False,
    )


# ─────────────────────────────── App-level singletons ────────────────────────
# Instantiated once at startup via lifespan; injected everywhere via get_db().

_engine:          AsyncEngine | None                    = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """Called once from app lifespan startup."""
    global _engine, _session_factory
    _engine          = build_engine(settings)
    _session_factory = build_session_factory(_engine)
    logger.info("DB engine initialised: pool_size=%s", settings.DB_POOL_SIZE)


async def close_db() -> None:
    """Called once from app lifespan shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("DB engine disposed.")
        _engine = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("DB engine not initialised. Call init_db() first.")
    return _engine


# ─────────────────────────────── FastAPI dependency ──────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an AsyncSession per request.
    Commits on success, rolls back on any exception.

    Usage:
        @router.get("/appointments")
        async def list_appts(db: AsyncSession = Depends(get_db)):
            ...
    """
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────── Context manager (non-FastAPI use) ───────────

@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Use this outside FastAPI (background tasks, CLI scripts, seed data).

    async with db_session() as session:
        result = await session.execute(select(User))
    """
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised. Call init_db() first.")

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ─────────────────────────────── DDL helpers ─────────────────────────────────

async def create_all_tables() -> None:
    """
    Dev / test helper — creates all tables from ORM metadata.
    Do NOT use in production; use Alembic migrations instead.
    """
    from habs_db.models import Base  # local import avoids circular deps

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All tables created (dev mode).")


async def drop_all_tables() -> None:
    """Test teardown only."""
    from habs_db.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("All tables dropped.")


# ─────────────────────────────── Health check ────────────────────────────────

async def ping_db() -> bool:
    """
    Lightweight connectivity check for /health endpoint.
    Returns True if DB is reachable, False otherwise.
    """
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("DB ping failed: %s", exc)
        return False
