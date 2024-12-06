import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.item_widget import ItemWidget
from ui.sku_widget import SkuWidget
from ui.tr_widget import TrWidget

@pytest.fixture
def app(qtbot):
    """Create QApplication instance"""
    return QApplication.instance() or QApplication([])

@pytest.fixture
def item_widget(app, qtbot):
    """Create ItemWidget instance"""
    widget = ItemWidget()
    qtbot.addWidget(widget)
    return widget

@pytest.fixture
def sku_widget(app, qtbot):
    """Create SkuWidget instance"""
    widget = SkuWidget()
    qtbot.addWidget(widget)
    return widget

class TestItemWidget:
    def test_init(self, item_widget):
        """Test initial widget state"""
        assert item_widget.delegate_mode == True
        assert item_widget.source_model is None
        assert hasattr(item_widget, 'table_view')

    def test_edit_mode(self, item_widget, qtbot):
        """Test edit mode toggle"""
        # Click edit mode button
        qtbot.mouseClick(item_widget.edit_mode, Qt.LeftButton)
        assert item_widget.edit_mode.isChecked()
        assert item_widget.source_model.is_editable

        # Click again to exit edit mode
        qtbot.mouseClick(item_widget.edit_mode, Qt.LeftButton)
        assert not item_widget.edit_mode.isChecked()
        assert not item_widget.source_model.is_editable

    def test_search_filter(self, item_widget, qtbot):
        """Test search filtering"""
        search_text = "test"
        qtbot.keyClicks(item_widget.search_bar, search_text)
        assert item_widget.proxy_model.filterRegExp().pattern() == search_text

class TestSkuWidget:
    def test_init(self, sku_widget):
        """Test initial widget state"""
        assert sku_widget.source_model is None
        assert hasattr(sku_widget, 'table_view')

    def test_edit_mode(self, sku_widget, qtbot):
        """Test edit mode toggle"""
        qtbot.mouseClick(sku_widget.edit_mode, Qt.LeftButton)
        assert sku_widget.edit_mode.isChecked()
        assert sku_widget.source_model.is_editable 