import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from ui.item_widget import ItemWidget
from model.item_model import ItemModel
from services.item_service import ItemService
from services.category_service import CategoryService
from model.category_model import CategoryModel

@pytest.fixture
def services(db_session):
    """Create services with test database session"""
    category_service = CategoryService()
    item_service = ItemService()
    return category_service, item_service

@pytest.fixture
async def models(services):
    """Create models"""
    category_service, item_service = services
    
    # Create and load category model
    category_model = CategoryModel(category_service)
    await category_model.load_data()
    
    # Create item model
    item_model = ItemModel("test_user", item_service, category_model)
    await item_model.load_data()
    
    return category_model, item_model

@pytest.fixture
async def widget(qtbot, models):
    """Create widget with models"""
    _, item_model = models
    widget = ItemWidget()
    widget.set_model(item_model)
    qtbot.addWidget(widget)
    return widget

def test_initial_state(widget):
    """Test initial widget state"""
    assert not widget.edit_mode.isChecked()
    assert widget.delegate_mode
    assert widget.table_view.model() is not None

@pytest.mark.asyncio
async def test_add_item(qtbot, widget, monkeypatch):
    """Test adding new item"""
    # Enable edit mode
    qtbot.mouseClick(widget.edit_mode, Qt.LeftButton)
    assert widget.edit_mode.isChecked()
    
    # Mock model's append_new_row
    called = False
    def mock_append():
        nonlocal called
        called = True
    monkeypatch.setattr(widget.model, "append_new_row", mock_append)
    
    # Click add button
    qtbot.mouseClick(widget.add_btn, Qt.LeftButton)
    assert called

@pytest.mark.asyncio
async def test_delete_item(qtbot, widget, monkeypatch):
    """Test deleting item"""
    # Enable edit mode
    qtbot.mouseClick(widget.edit_mode, Qt.LeftButton)
    
    # Mock QMessageBox.question to return Yes
    monkeypatch.setattr(QMessageBox, "question", 
                       lambda *args: QMessageBox.Yes)
    
    # Mock model's set_del_flag
    called_with = None
    def mock_set_del_flag(indexes):
        nonlocal called_with
        called_with = indexes
    monkeypatch.setattr(widget.model, "set_del_flag", mock_set_del_flag)
    
    # Select first row
    index = widget.proxy_model.index(0, 0)
    widget.table_view.setCurrentIndex(index)
    
    # Click delete button
    qtbot.mouseClick(widget.delete_btn, Qt.LeftButton)
    assert called_with is not None

@pytest.mark.asyncio
async def test_save_changes(qtbot, widget, monkeypatch):
    """Test saving changes"""
    # Enable edit mode
    qtbot.mouseClick(widget.edit_mode, Qt.LeftButton)
    
    # Mock model's save_changes
    called = False
    async def mock_save():
        nonlocal called
        called = True
    monkeypatch.setattr(widget.model, "save_changes", mock_save)
    
    # Click save button
    qtbot.mouseClick(widget.save_btn, Qt.LeftButton)
    assert called
    assert not widget.edit_mode.isChecked()

def test_search_filter(qtbot, widget):
    """Test search filtering"""
    # Type in search bar
    qtbot.keyClicks(widget.search_bar, "test")
    
    # Check if filter is applied
    assert widget.proxy_model.filterRegExp().pattern() == "test"

def test_double_click(qtbot, widget, monkeypatch):
    """Test row double click"""
    # Mock parent's item_selected method
    called_with = None
    def mock_item_selected(item_id):
        nonlocal called_with
        called_with = item_id
    monkeypatch.setattr(widget.parent, "item_selected", mock_item_selected)
    
    # Double click first row
    index = widget.proxy_model.index(0, 0)
    qtbot.mouseDClick(widget.table_view.viewport(), Qt.LeftButton, pos=widget.table_view.visualRect(index).center())
    
    assert called_with is not None

def test_edit_mode_validation(qtbot, widget, monkeypatch):
    """Test edit mode validation"""
    # Mock model's is_model_editing to return True
    monkeypatch.setattr(widget.model, "is_model_editing", lambda: True)
    
    # Mock QMessageBox.warning
    warning_shown = False
    def mock_warning(*args):
        nonlocal warning_shown
        warning_shown = True
    monkeypatch.setattr(QMessageBox, "warning", mock_warning)
    
    # Try to enable edit mode
    qtbot.mouseClick(widget.edit_mode, Qt.LeftButton)
    assert not widget.edit_mode.isChecked()
    assert warning_shown 