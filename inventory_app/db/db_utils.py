from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from constants import ConfigReader
from common.d_logger import Logs
from .models import Base
from contextlib import asynccontextmanager

logger = Logs().get_logger("db")

class DbUtil:
    _instance = None
    _loop = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DbUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not hasattr(self, 'engine'):
            config = ConfigReader()
            self.engine = create_async_engine(
                f"postgresql+asyncpg://{config.get_options('User')}:{config.get_options('Password')}"
                f"@{config.get_options('Host')}:{config.get_options('Port')}/{config.get_options('Database')}",
                echo=True
            )
            self.async_session = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

    @classmethod
    def set_loop(cls, loop):
        """Set the event loop to be used by all DbUtil instances"""
        cls._loop = loop

    @classmethod
    def get_loop(cls):
        """Get the current event loop"""
        return cls._loop

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def get_session(self):
        """Returns an async session context manager"""
        return self.async_session()

    @asynccontextmanager
    async def session(self):
        """Provides a session context manager that automatically handles commit/rollback"""
        session = self.async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()