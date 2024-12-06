import pytest
import asyncio
from qasync import QEventLoop
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance"""
    app = QApplication.instance() or QApplication([])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    yield app
    app.quit()

@pytest.fixture
def mock_db(monkeypatch):
    """Mock database for testing"""
    class MockDB:
        async def create_tables(self):
            pass
            
        async def drop_tables(self):
            pass
            
    monkeypatch.setattr("db.db_utils.DbUtil", MockDB) 