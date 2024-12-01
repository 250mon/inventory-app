from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from constants import ConfigReader
from common.d_logger import Logs
from .models import Base
from contextlib import asynccontextmanager
import asyncio
import qasync
from common.singleton import Singleton

logger = Logs().get_logger("db")

class DbUtil(metaclass=Singleton):
    def __init__(self):
        config = ConfigReader()
        self.engine = create_async_engine(
            f"postgresql+asyncpg://{config.get_options('User')}:{config.get_options('Password')}"
            f"@{config.get_options('Host')}:{config.get_options('Port')}/{config.get_options('Database')}",
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