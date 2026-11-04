"""Async and sync SQLAlchemy database setup."""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

sync_engine = create_engine(
    settings.database_url_sync,
    connect_args={"check_same_thread": False},
)

SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def init_db() -> None:
    from app import models  # noqa: F401

    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    (settings.reports_dir.parent / "data").mkdir(parents=True, exist_ok=True)

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_orders_v2)


def _migrate_orders_v2(connection) -> None:
    """Add Enterprise v2 columns to existing SQLite orders table."""
    from sqlalchemy import inspect, text

    insp = inspect(connection)
    if "orders" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("orders")}
    alters = [
        ("selected_parts_json", "TEXT"),
        ("parts_pricing_json", "TEXT"),
        ("total_amount", "REAL DEFAULT 0"),
        ("payment_plan", "VARCHAR(32) DEFAULT 'full'"),
        ("paid_amount", "REAL DEFAULT 0"),
        ("milestones_json", "TEXT"),
        ("client_access_token", "VARCHAR(64)"),
    ]
    for col, typedef in alters:
        if col not in existing:
            connection.execute(text(f"ALTER TABLE orders ADD COLUMN {col} {typedef}"))
