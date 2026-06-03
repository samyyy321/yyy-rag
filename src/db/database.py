"""SQLAlchemy 业务数据库引擎和请求级 Session。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import get_settings


# 引擎只负责连接池配置；表结构创建和升级统一交给 Alembic。
engine = create_engine(
    get_settings().DATABASE_URL,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """为每个 FastAPI 请求提供独立数据库 Session，并在结束时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
