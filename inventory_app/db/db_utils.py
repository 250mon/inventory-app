from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import Config
from common.d_logger import Logs
from .models import Base
from contextlib import asynccontextmanager
from common.singleton import Singleton

logger = Logs().get_logger("db")

class DbUtil(metaclass=Singleton):
    def __init__(self):
        self.engine = create_async_engine(
            f"postgresql+asyncpg://{Config.DB_USER}:{Config.DB_PASSWORD}"
            f"@{Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}",
            echo=True,
            future=True
        )
        self.async_session = sessionmaker(
            class_=AsyncSession, 
            expire_on_commit=False,
            bind=self.engine
        )

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def session(self):
        """Provides a session context manager that automatically handles commit/rollback"""
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            await session.close()