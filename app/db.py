"""SQLite log of all webhook events."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class WebhookLog(Base):
    __tablename__ = "webhook_log"
    id = Column(Integer, primary_key=True)
    integration_name = Column(String, index=True)
    event_type = Column(String, index=True)
    status = Column(String)            # received | delivered | failed | duplicate
    payload = Column(Text)             # raw JSON
    error = Column(Text, nullable=True)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


_engine = None
_factory = None


async def init_db():
    global _engine, _factory
    db_path = os.environ.get("BRIDGE_DB", "bridge.db")
    _engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    _factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_session():
    if _factory is None:
        raise RuntimeError("DB not initialized — call init_db() first")
    return _factory()
