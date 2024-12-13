import pytest
from datetime import date, timedelta
from model.sku_model import SkuModel
from model.item_model import ItemModel
from model.category_model import CategoryModel
from model.models import SKU, Item, Category

@pytest.fixture
async def category_model():
    """Fixture to provide a CategoryModel instance"""
    model = CategoryModel()
    yield model

@pytest.fixture
async def item_model():
    """Fixture to provide an ItemModel instance"""
    model = ItemModel(user_name="admin")
    yield model

@pytest.fixture
async def sku_model():
    """Fixture to provide a SKUModel instance"""
    model = SkuModel()
    yield model

@pytest.fixture
async def sample_category(category_model):
    """Fixture to provide a sample category"""
    category_data = {
        'category_name': 'Test Category'
    }
    category = await category_model.create_category(category_data)
    yield category
    try:
        await category_model.delete_category(category.category_id)
    except:
        pass

@pytest.fixture
async def sample_item(item_model, sample_category):
    """Fixture to provide a sample item"""
    item_data = {
        'item_name': 'Test Item',
        'category_id': sample_category.category_id,
        'active': True,
        'description': 'Test Description'
    }
    item = await item_model.create_item(item_data)
    yield item
    try:
        await item_model.delete_item(item.item_id)
    except:
        pass

@pytest.fixture
async def sample_sku(sku_model, sample_item):
    """Fixture to provide a sample SKU"""
    sku_data = {
        'root_sku': 0,
        'sub_name': 'Test SKU',
        'bit_code': 'TEST001',
        'sku_qty': 10,
        'min_qty': 2,
        'item_id': sample_item.item_id,
        'active': True,
        'description': 'Test Description'
    }
    sku = await sku_model.create_sku(sku_data)
    yield sku
    try:
        await sku_model.delete_sku(sku.sku_id)
    except:
        pass

class TestSKUModel:
    """Test cases for SKUModel"""

    async def test_create_sku(self, sku_model, sample_item):
        """Test creating a new SKU"""
        sku_data = {
            'root_sku': 0,
            'sub_name': 'New SKU',
            'bit_code': 'NEW001',
            'sku_qty': 5,
            'min_qty': 2,
            'item_id': sample_item.item_id,
            'active': True,
            'description': 'Description'
        }
        
        sku = await sku_model.create_sku(sku_data)
        assert sku is not None
        assert sku.sub_name == sku_data['sub_name']
        assert sku.bit_code == sku_data['bit_code']
        assert sku.sku_qty == sku_data['sku_qty']
        
        # Cleanup
        await sku_model.delete_sku(sku.sku_id)

    async def test_get_sku(self, sku_model, sample_sku):
        """Test retrieving a SKU by ID"""
        sku = await sku_model.get_sku(sample_sku.sku_id)
        assert sku is not None
        assert sku.sub_name == sample_sku.sub_name
        assert sku.sku_qty == sample_sku.sku_qty

    async def test_get_all_skus(self, sku_model, sample_sku):
        """Test retrieving all SKUs"""
        skus = await sku_model.get_all_skus()
        assert len(skus) > 0
        assert any(s.sku_id == sample_sku.sku_id for s in skus)

    async def test_get_skus_by_item(self, sku_model, sample_sku, sample_item):
        """Test retrieving SKUs for specific item"""
        skus = await sku_model.get_all_skus(item_id=sample_item.item_id)
        assert len(skus) > 0
        assert all(s.item_id == sample_item.item_id for s in skus)

    async def test_update_sku(self, sku_model, sample_sku):
        """Test updating an existing SKU"""
        updated_data = {
            'sub_name': 'Updated SKU',
            'bit_code': 'UPD001',
            'sku_qty': 15,
            'min_qty': 3,
            'active': False,
            'description': 'Updated Description'
        }
        
        updated_sku = await sku_model.update_sku(sample_sku.sku_id, updated_data)
        assert updated_sku is not None
        assert updated_sku.sub_name == updated_data['sub_name']
        assert updated_sku.sku_qty == updated_data['sku_qty']
        assert updated_sku.active == updated_data['active']

    async def test_delete_sku(self, sku_model, sample_item):
        """Test deleting a SKU"""
        sku_data = {
            'root_sku': 0,
            'sub_name': 'To Delete',
            'bit_code': 'DEL001',
            'sku_qty': 5,
            'min_qty': 2,
            'item_id': sample_item.item_id,
            'active': True,
            'description': 'Will be deleted'
        }
        sku = await sku_model.create_sku(sku_data)
        
        result = await sku_model.delete_sku(sku.sku_id)
        assert result is True
        
        deleted_sku = await sku_model.get_sku(sku.sku_id)
        assert deleted_sku is None

    async def test_root_sku_validation(self, item_model, sku_model, sample_category, sample_sku, sample_item):
        """Test validation of root SKU relationships"""
        # Create a SKU with sample_sku as root
        child_sku_data = {
            'root_sku': sample_sku.sku_id,
            'sub_name': 'Child SKU',
            'bit_code': 'CHILD001',
            'sku_qty': 2,
            'min_qty': 1,
            'item_id': sample_item.item_id,
            'active': True
        }
        
        # Should succeed - valid root SKU
        is_valid = await sku_model.validate_sku(
            child_sku_data['root_sku'],
            child_sku_data['item_id']
        )
        assert is_valid
        
        # Should fail - root SKU from different item
        invalid = await sku_model.validate_sku(
            999999,  # Non-existent SKU
            child_sku_data['item_id']
        )
        assert not invalid
        
        # Create SKU with different item_id
        different_item = await item_model.create_item({
            'item_name': 'Different Item',
            'category_id': sample_category.category_id,
            'active': True,
            'description': 'Description'
        })
        
        different_sku = await sku_model.create_sku({
            'root_sku': 0,
            'sub_name': 'Different SKU',
            'bit_code': 'DIFF001',
            'sku_qty': 5,
            'min_qty': 2,
            'item_id': different_item.item_id,
            'active': True
        })
        
        # Should fail - root SKU belongs to different item
        invalid = await sku_model.validate_sku(
            different_sku.sku_id,
            child_sku_data['item_id']
        )
        assert not invalid
        
        # Cleanup
        print(f"Deleting different item: {different_item.item_id}")
        await item_model.delete_item(different_item.item_id)

    async def test_sku_quantity_validation(self, sku_model, sample_item):
        """Test SKU quantity validation"""
        # Create a root SKU
        root_sku_data = {
            'root_sku': 0,
            'sub_name': 'Root SKU',
            'bit_code': 'ROOT001',
            'sku_qty': 10,  # Total should match sum of sub-SKUs
            'min_qty': 2,
            'item_id': sample_item.item_id,
            'active': True,
            'description': 'Root SKU'
        }
        root_sku = await sku_model.create_sku(root_sku_data)

        # Create sub-SKUs
        sub_sku_data1 = {
            'root_sku': root_sku.sku_id,
            'sub_name': 'Sub SKU 1',
            'bit_code': 'SUB001',
            'sku_qty': 4,
            'min_qty': 1,
            'item_id': sample_item.item_id,
            'active': True,
            'description': 'Sub SKU 1'
        }
        sub_sku_data2 = {
            'root_sku': root_sku.sku_id,
            'sub_name': 'Sub SKU 2',
            'bit_code': 'SUB002',
            'sku_qty': 6,
            'min_qty': 1,
            'item_id': sample_item.item_id,
            'active': True,
            'description': 'Sub SKU 2'
        }
        
        sub_sku1 = await sku_model.create_sku(sub_sku_data1)
        sub_sku2 = await sku_model.create_sku(sub_sku_data2)

        try:
            # Test with correct total quantity (4 + 6 = 10)
            is_correct = await sku_model.is_sku_qty_correct(root_sku.sku_id, 10)
            assert is_correct, "Quantity should be correct when matching sum of sub-SKUs"

            # Test with incorrect quantity
            is_incorrect = await sku_model.is_sku_qty_correct(root_sku.sku_id, 15)
            assert not is_incorrect, "Quantity should be incorrect when not matching sum of sub-SKUs"

            # Test SKU with no sub-SKUs
            no_subs = await sku_model.is_sku_qty_correct(sub_sku1.sku_id, 4)
            assert no_subs, "SKU with no sub-SKUs should always return True"

        finally:
            # Cleanup - delete in reverse order (sub-SKUs first, then root)
            await sku_model.delete_sku(sub_sku2.sku_id)
            await sku_model.delete_sku(sub_sku1.sku_id)
            await sku_model.delete_sku(root_sku.sku_id)

    async def test_load_data(self, sku_model, sample_sku):
        """Test loading data into the Qt model"""
        # Test loading all SKUs
        await sku_model.load_data()
        assert len(sku_model._data) > 0
        assert any(s.sku_id == sample_sku.sku_id for s in sku_model._data)
        
        # Test loading SKUs for specific item
        await sku_model.load_data(item_id=sample_sku.item_id)
        assert len(sku_model._data) > 0
        assert all(s.item_id == sample_sku.item_id for s in sku_model._data)
        
        # Test loading SKUs for non-existent item
        await sku_model.load_data(item_id=999999)
        assert len(sku_model._data) == 0

    async def test_inactive_items(self, sku_model, sample_sku):
        """Test handling of inactive items"""
        await sku_model.load_data(item_id=sample_sku.item_id)
        
        # Test showing/hiding inactive items
        sku_model.show_inactive_items = False
        assert sku_model.is_active_row(0)  # First row should be active
        
        # Update SKU to inactive
        await sku_model.update_sku(sample_sku.sku_id, {'active': False})
        await sku_model.load_data(item_id=sample_sku.item_id)
        
        # Should not show inactive SKU
        assert not any(s.sku_id == sample_sku.sku_id for s in sku_model._data)
        
        # Should show when including inactive
        sku_model.show_inactive_items = True
        await sku_model.load_data(item_id=sample_sku.item_id)
        assert any(s.sku_id == sample_sku.sku_id for s in sku_model._data)

    async def test_create_empty_sku(self, sku_model):
        """Test creating an empty SKU object"""
        empty_sku = sku_model.create_empty_sku()
        assert isinstance(empty_sku, SKU)
        assert empty_sku.sku_id == 0
        assert empty_sku.root_sku == 0
        assert empty_sku.active is True
        assert empty_sku.sku_qty == 0
        assert empty_sku.min_qty > 0  # Should have default min quantity

    async def test_expiration_date(self, sku_model, sample_item):
        """Test SKU expiration date handling"""
        future_date = date.today() + timedelta(days=30)
        sku_data = {
            'root_sku': 0,
            'sub_name': 'Expiring SKU',
            'bit_code': 'EXP001',
            'sku_qty': 5,
            'min_qty': 2,
            'item_id': sample_item.item_id,
            'active': True,
            'expiration_date': future_date
        }
        
        sku = await sku_model.create_sku(sku_data)
        assert sku.expiration_date == future_date
        
        # Cleanup
        await sku_model.delete_sku(sku.sku_id) 

    async def test_pagination(self, sku_model, sample_item):
        """Test SKU data pagination"""
        # Create multiple SKUs
        skus = []
        for i in range(SkuModel.PAGE_SIZE + 5):  # Create more than one page
            sku_data = {
                'root_sku': 0,
                'sub_name': f'SKU {i}',
                'bit_code': f'TEST{i:03d}',
                'sku_qty': 5,
                'min_qty': 2,
                'item_id': sample_item.item_id,
                'active': True
            }
            sku = await sku_model.create_sku(sku_data)
            skus.append(sku)

        # Test initial load
        await sku_model.load_data(item_id=sample_item.item_id)
        assert len(sku_model._data) == SkuModel.PAGE_SIZE
        
        # Test loading more
        assert sku_model.can_load_more()
        more_loaded = await sku_model.load_more()
        assert more_loaded
        assert len(sku_model._data) > SkuModel.PAGE_SIZE

        # Cleanup
        for sku in skus:
            await sku_model.delete_sku(sku.sku_id)