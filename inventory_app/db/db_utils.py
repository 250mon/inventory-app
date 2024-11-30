from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from constants import ConfigReader
from common.d_logger import Logs
from .models import Base
from contextlib import asynccontextmanager
import asyncio

logger = Logs().get_logger("db")

class DbUtil:
    _instance = None
    _loop = None

    # Singleton pattern
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DbUtil, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Only initialize once
        if not hasattr(self, 'engine'):
            config = ConfigReader()
            if not self._loop:
                raise RuntimeError("Event loop must be set using set_loop() before initializing DbUtil")
            
            asyncio.set_event_loop(self._loop)
            
            self.engine = create_async_engine(
                f"postgresql+asyncpg://{config.get_options('User')}:{config.get_options('Password')}"
                f"@{config.get_options('Host')}:{config.get_options('Port')}/{config.get_options('Database')}",
                echo=True
            )
            self.async_session = sessionmaker(
                class_=AsyncSession, 
                expire_on_commit=False,
                bind=self.engine
            )

    @classmethod
    def set_loop(cls, loop):
        """Set the event loop to be used by all DbUtil instances"""
        logger.debug(f"Setting DbUtil loop id: {id(loop)}")
        cls._loop = loop
        asyncio.set_event_loop(loop)

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

    @asynccontextmanager
    async def session(self):
        """Provides a session context manager that automatically handles commit/rollback"""
        if asyncio.get_event_loop() != self._loop:
            asyncio.set_event_loop(self._loop)
        
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