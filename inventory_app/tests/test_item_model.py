import pytest
from model.item_model import ItemModel
from model.models import Item, Category
from model.category_model import CategoryModel
from config import Config

@pytest.fixture
async def category_model():
    """Fixture to provide a CategoryModel instance"""
    model = CategoryModel()
    yield model

@pytest.fixture
async def item_model(category_model):
    """Fixture to provide an ItemModel instance"""
    model = ItemModel(user_name="admin")  # Using admin for full access
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

class TestItemModel:
    """Test cases for ItemModel"""

    async def test_create_item(self, item_model, sample_category):
        """Test creating a new item"""
        item_data = {
            'item_name': 'New Item',
            'category_id': sample_category.category_id,
            'active': True,
            'description': 'Description'
        }
        
        item = await item_model.create_item(item_data)
        assert item is not None
        assert item.item_name == item_data['item_name']
        assert item.category_id == item_data['category_id']
        assert item.active == item_data['active']
        assert item.description == item_data['description']
        
        # Cleanup
        await item_model.delete_item(item.item_id)

    async def test_get_item(self, item_model, sample_item):
        """Test retrieving an item by ID"""
        item = await item_model.get_item(sample_item.item_id)
        assert item is not None
        assert item.item_name == sample_item.item_name
        assert item.category_id == sample_item.category_id
        assert item.description == sample_item.description

    async def test_get_item_by_name(self, item_model, sample_item):
        """Test retrieving an item by name"""
        item = await item_model.get_item_by_name(sample_item.item_name)
        assert item is not None
        assert item.item_id == sample_item.item_id
        assert item.category_id == sample_item.category_id

    async def test_get_all_items(self, item_model, sample_item):
        """Test retrieving all items"""
        items = await item_model.get_all_items()
        assert len(items) > 0
        assert any(i.item_id == sample_item.item_id for i in items)

    async def test_get_all_items_with_inactive(self, item_model, sample_item):
        """Test retrieving all items including inactive ones"""
        # Create an inactive item
        inactive_item = await item_model.create_item({
            'item_name': 'Inactive Item',
            'category_id': sample_item.category_id,
            'active': False,
            'description': 'Inactive'
        })
        
        # Test without inactive items
        active_items = await item_model.get_all_items(include_inactive=False)
        assert not any(i.item_id == inactive_item.item_id for i in active_items)
        
        # Test with inactive items
        all_items = await item_model.get_all_items(include_inactive=True)
        assert any(i.item_id == inactive_item.item_id for i in all_items)
        
        # Cleanup
        await item_model.delete_item(inactive_item.item_id)

    async def test_update_item(self, item_model, sample_item, sample_category):
        """Test updating an existing item"""
        updated_data = {
            'item_name': 'Updated Item',
            'category_id': sample_category.category_id,
            'active': False,
            'description': 'Updated Description'
        }
        
        updated_item = await item_model.update_item(
            sample_item.item_id, 
            updated_data
        )
        
        assert updated_item is not None
        assert updated_item.item_name == updated_data['item_name']
        assert updated_item.active == updated_data['active']
        assert updated_item.description == updated_data['description']

    async def test_delete_item(self, item_model, sample_category):
        """Test deleting an item"""
        item_data = {
            'item_name': 'To Delete',
            'category_id': sample_category.category_id,
            'active': True,
            'description': 'Will be deleted'
        }
        item = await item_model.create_item(item_data)
        
        result = await item_model.delete_item(item.item_id)
        assert result is True
        
        deleted_item = await item_model.get_item(item.item_id)
        assert deleted_item is None

    async def test_load_data(self, item_model, sample_item):
        """Test loading data into the Qt model"""
        await item_model.load_data()
        assert len(item_model._data) > 0
        assert any(i.item_id == sample_item.item_id for i in item_model._data)

    async def test_validate_item(self, item_model, sample_item):
        """Test item validation"""
        await item_model.load_data()
        
        # Test with existing name (should fail)
        assert not item_model.validate_item(sample_item.item_name)
        
        # Test with new name (should pass)
        assert item_model.validate_item("New Unique Name")
        
        # Test with empty name (should fail)
        assert not item_model.validate_item("")
        
        # Test with existing name but excluding current ID (should pass)
        assert item_model.validate_item(
            sample_item.item_name, 
            sample_item.item_id
        )

    async def test_create_empty_item(self, item_model):
        """Test creating an empty item object"""
        empty_item = item_model.create_empty_item()
        assert isinstance(empty_item, Item)
        assert empty_item.item_id == 0
        assert empty_item.item_name == ''
        assert empty_item.active is True
        assert empty_item.category_id == 0
        assert empty_item.description == ''

    async def test_duplicate_item_name(self, item_model, sample_item):
        """Test that creating an item with duplicate name fails"""
        duplicate_data = {
            'item_name': sample_item.item_name,
            'category_id': sample_item.category_id,
            'active': True,
            'description': 'Different description'
        }
        
        with pytest.raises(Exception):  # Should raise some form of database error
            await item_model.create_item(duplicate_data)

    async def test_user_privilege(self, item_model):
        """Test user privilege levels"""
        # Test admin privilege
        admin_model = ItemModel(user_name="admin")
        assert admin_model.get_user_privilege() == Config.UserPrivilege.Admin
        
        # Test regular user privilege
        user_model = ItemModel(user_name="regular_user")
        assert user_model.get_user_privilege() == Config.UserPrivilege.User

    async def test_is_active_row(self, item_model, sample_item):
        """Test active row checking"""
        await item_model.load_data()
        
        # Test active item
        assert item_model.is_active_row(0)  # Assuming sample_item is first row
        
        # Create inactive item and test
        inactive_item = await item_model.create_item({
            'item_name': 'Inactive Item',
            'category_id': sample_item.category_id,
            'active': False,
            'description': 'Inactive'
        })
        
        # Ensure load_data includes inactive items
        await item_model.load_data(include_inactive=True)
        
        # Find the index of the inactive item
        try:
            inactive_index = next(
                i for i, item in enumerate(item_model._data)
                if item.item_id == inactive_item.item_id
            )
            assert not item_model.is_active_row(inactive_index)
        except StopIteration:
            pytest.fail("Inactive item not found in loaded data")
        
        # Cleanup
        await item_model.delete_item(inactive_item.item_id) 