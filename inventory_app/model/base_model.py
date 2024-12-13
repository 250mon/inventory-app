from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import Config
from common.d_logger import Logs
from contextlib import asynccontextmanager
from model.models import Base

logger = Logs().get_logger("main")

class BaseDBModel:
    """Base class for database models providing SQLAlchemy connection handling"""
    
    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    _async_session = sessionmaker(
        class_=AsyncSession,
        expire_on_commit=False,
        bind=_engine
    )

    @classmethod
    @asynccontextmanager
    async def session(cls):
        """Provides a session context manager that automatically handles commit/rollback"""
        session = cls._async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            await session.close()

    @classmethod
    async def create_tables(cls):
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def drop_tables(cls):
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all) 