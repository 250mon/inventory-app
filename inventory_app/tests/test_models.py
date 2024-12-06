import pytest
from PySide6.QtCore import Qt, QModelIndex
from model.item_model import ItemModel
from model.sku_model import SkuModel
from constants import EditLevel, RowFlags

@pytest.fixture
def item_model():
    """Fixture to create a fresh ItemModel instance"""
    model = ItemModel("test_user")
    return model

@pytest.fixture
def sku_model(item_model):
    """Fixture to create a fresh SkuModel instance"""
    model = SkuModel("test_user", item_model)
    return model

class TestItemModel:
    def test_init(self, item_model):
        """Test initial state of ItemModel"""
        assert item_model.table_name == 'items'
        assert item_model.user_name == 'test_user'
        assert not item_model.is_editable
        assert item_model.edit_level == EditLevel.UserModifiable

    def test_column_setup(self, item_model):
        """Test column configuration"""
        expected_columns = [
            'item_id', 'active', 'item_name', 'category_name',
            'description', 'category_id', 'flag'
        ]
        assert item_model.column_names == expected_columns

    def test_add_new_row(self, item_model):
        """Test adding a new row"""
        initial_count = item_model.rowCount()
        item_model.append_new_row()
        
        assert item_model.rowCount() == initial_count + 1
        
        # Check new row has correct flag
        new_row_idx = item_model.index(item_model.rowCount() - 1, 
                                     item_model.get_col_number('flag'))
        assert item_model.data(new_row_idx) == RowFlags.NewRow

    def test_data_display(self, item_model):
        """Test data display formatting"""
        item_model.append_new_row()
        row = item_model.rowCount() - 1
        
        # Test active column display
        active_idx = item_model.index(row, item_model.get_col_number('active'))
        assert item_model.data(active_idx, Qt.DisplayRole) in ['Y', 'N']

        # Test numeric column display
        id_idx = item_model.index(row, item_model.get_col_number('item_id'))
        assert isinstance(item_model.data(id_idx, Qt.DisplayRole), str)
        assert isinstance(item_model.data(id_idx, item_model.SortRole), int)

class TestSkuModel:
    def test_init(self, sku_model):
        """Test initial state of SkuModel"""
        assert sku_model.table_name == 'skus'
        assert sku_model.user_name == 'test_user'
        assert not sku_model.is_editable
        assert sku_model.selected_upper_id is None

    def test_column_setup(self, sku_model):
        """Test column configuration"""
        expected_columns = [
            'sku_id', 'root_sku', 'item_name', 'sub_name', 'active',
            'sku_qty', 'min_qty', 'expiration_date', 'description',
            'bit_code', 'sku_name', 'item_id', 'flag'
        ]
        assert sku_model.column_names == expected_columns

    def test_add_new_row_without_item(self, sku_model):
        """Test adding new row fails without selected item"""
        with pytest.raises(Exception):
            sku_model.append_new_row()

    def test_sku_qty_validation(self, sku_model):
        """Test SKU quantity validation"""
        sku_id = 1
        qty = 10
        assert sku_model.is_sku_qty_correct(sku_id, qty) == True 