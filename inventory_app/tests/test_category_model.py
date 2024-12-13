import pytest
from model.category_model import CategoryModel
from model.models import Category

@pytest.fixture
async def category_model():
    """Fixture to provide a CategoryModel instance"""
    model = CategoryModel()
    yield model

@pytest.fixture
async def sample_category(category_model):
    """Fixture to provide a sample category"""
    category_data = {
        'category_name': 'Test Category'
    }
    category = await category_model.create_category(category_data)
    yield category
    # Cleanup
    try:
        await category_model.delete_category(category.category_id)
    except:
        pass

class TestCategoryModel:
    """Test cases for CategoryModel"""

    async def test_create_category(self, category_model):
        """Test creating a new category"""
        category_data = {
            'category_name': 'New Category'
        }
        
        category = await category_model.create_category(category_data)
        assert category is not None
        assert category.category_name == category_data['category_name']
        
        # Cleanup
        await category_model.delete_category(category.category_id)

    async def test_get_category(self, category_model, sample_category):
        """Test retrieving a category by ID"""
        category = await category_model.get_category(sample_category.category_id)
        assert category is not None
        assert category.category_name == sample_category.category_name

    async def test_get_category_by_name(self, category_model, sample_category):
        """Test retrieving a category by name"""
        category = await category_model.get_category_by_name(sample_category.category_name)
        assert category is not None
        assert category.category_id == sample_category.category_id

    async def test_get_all_categories(self, category_model, sample_category):
        """Test retrieving all categories"""
        categories = await category_model.get_all_categories()
        assert len(categories) > 0
        assert any(c.category_id == sample_category.category_id for c in categories)

    async def test_update_category(self, category_model, sample_category):
        """Test updating a category"""
        updated_data = {
            'category_name': 'Updated Category'
        }
        
        updated_category = await category_model.update_category(
            sample_category.category_id, 
            updated_data
        )
        
        assert updated_category is not None
        assert updated_category.category_name == updated_data['category_name']

    async def test_delete_category(self, category_model):
        """Test deleting a category"""
        # Create a category to delete
        category_data = {
            'category_name': 'To Delete'
        }
        category = await category_model.create_category(category_data)
        
        # Delete it
        result = await category_model.delete_category(category.category_id)
        assert result is True
        
        # Verify it's gone
        deleted_category = await category_model.get_category(category.category_id)
        assert deleted_category is None

    async def test_load_data(self, category_model, sample_category):
        """Test loading data into the Qt model"""
        await category_model.load_data()
        assert len(category_model._data) > 0
        assert any(c.category_id == sample_category.category_id 
                  for c in category_model._data)

    async def test_get_category_names(self, category_model, sample_category):
        """Test getting list of category names"""
        await category_model.load_data()
        names = category_model.get_category_names()
        assert isinstance(names, list)
        assert sample_category.category_name in names

    async def test_validate_category(self, category_model, sample_category):
        """Test category validation"""
        await category_model.load_data()
        
        # Test with existing name (should fail)
        assert not category_model.validate_category(sample_category.category_name)
        
        # Test with new name (should pass)
        assert category_model.validate_category("New Unique Name")
        
        # Test with empty name (should fail)
        assert not category_model.validate_category("")
        
        # Test with existing name but excluding current ID (should pass)
        assert category_model.validate_category(
            sample_category.category_name, 
            sample_category.category_id
        )

    async def test_create_empty_category(self, category_model):
        """Test creating an empty category object"""
        empty_category = category_model.create_empty_category()
        assert isinstance(empty_category, Category)
        assert empty_category.category_id == 0
        assert empty_category.category_name == ''

    async def test_duplicate_category_name(self, category_model, sample_category):
        """Test that creating a category with duplicate name fails"""
        duplicate_data = {
            'category_name': sample_category.category_name
        }
        
        with pytest.raises(Exception):  # Should raise some form of database error
            await category_model.create_category(duplicate_data)

    async def test_update_nonexistent_category(self, category_model):
        """Test updating a category that doesn't exist"""
        result = await category_model.update_category(999999, {
            'category_name': 'New Name'
        })
        assert result is None

    async def test_delete_nonexistent_category(self, category_model):
        """Test deleting a category that doesn't exist"""
        result = await category_model.delete_category(999999)
        assert result is False 