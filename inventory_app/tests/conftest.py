import pytest
import asyncio
import asyncio
from qasync import QEventLoop
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Base, Category, Item, User
import os

TEST_DB_URL = os.getenv(
    'TEST_DB_URL',
    "postgresql+asyncpg://postgres:123abc@192.168.11.14:5433/danaul_inventory"
)

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session():
    """Create test database session"""
    # Create test database engine
    engine = create_async_engine(
        TEST_DB_URL,
        echo=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Clean slate
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Create and yield session
    async with async_session() as session:
        yield session
        
        # Rollback any pending transactions
        await session.rollback()
        
    # Clean up
    await engine.dispose()

@pytest.fixture
async def test_data(db_session):
    """Create test data"""
    # Create test user
    user = User(user_name="test_user", user_password="test_pass")
    db_session.add(user)
    
    # Create test categories
    categories = [
        Category(category_name="Test Category 1"),
        Category(category_name="Test Category 2")
    ]
    for category in categories:
        db_session.add(category)
    
    # Create test items
    items = [
        Item(
            item_name="Test Item 1",
            category_id=1,
            active=True,
            description="Test description 1"
        ),
        Item(
            item_name="Test Item 2", 
            category_id=1,
            active=True,
            description="Test description 2"
        )
    ]
    for item in items:
        db_session.add(item)
    
    await db_session.commit()
    return db_session 