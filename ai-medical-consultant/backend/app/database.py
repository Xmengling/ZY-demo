# -*- coding: utf-8 -*-
"""数据库连接与会话管理（SQLAlchemy 2.0）。"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：提供请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  确保模型注册到 metadata

    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def _run_lightweight_migrations() -> None:
    """对已存在的表做最小列补齐（适配 SQLite，无需 Alembic）。"""
    inspector = inspect(engine)
    if "knowledge_docs" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("knowledge_docs")}
    if "source" not in columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE knowledge_docs ADD COLUMN source VARCHAR(256) DEFAULT ''")
            )
