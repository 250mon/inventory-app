import pytest
from datetime import datetime, date
from model.transaction_model import TransactionModel
from model.sku_model import SkuModel
from model.item_model import ItemModel
from model.category_model import CategoryModel
from model.models import Transaction, TransactionType, SKU, Item, Category
from config import Config

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
async def transaction_model():
    """Fixture to provide a TransactionModel instance"""
    model = TransactionModel()
    yield model

@pytest.fixture
async def sample_category(category_model):
    """Fixture to provide a sample category"""
    category_data = {
        'category_name': 'Test Category'
    }
    category = await category_model.create_category(category_data)
    yield category
    await category_model.delete_category(category.category_id)

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
    await item_model.delete_item(item.item_id)

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
    await sku_model.delete_sku(sku.sku_id)

@pytest.fixture
async def transaction_types():
    """Fixture to provide transaction types"""
    return {
        'BUY': 1,
        'SELL': 2,
        'ADJUSTMENT_PLUS': 3,
        'ADJUSTMENT_MINUS': 4
    }

class TestTransactionModel:
    """Test cases for TransactionModel"""

    async def test_create_transaction(self, transaction_model, sample_sku, transaction_types):
        """Test creating a new transaction"""
        transaction_data = {
            'sku_id': sample_sku.sku_id,
            'tr_type_id': transaction_types['BUY'],
            'tr_qty': 5,
            'before_qty': sample_sku.sku_qty,
            'after_qty': sample_sku.sku_qty + 5,
            'tr_timestamp': datetime.now(),
            'description': 'Test transaction',
            'user_id': 1  # Assuming admin user_id is 1
        }
        
        transaction = await transaction_model.create_transaction(transaction_data)
        assert transaction is not None
        assert transaction.sku_id == transaction_data['sku_id']
        assert transaction.tr_qty == transaction_data['tr_qty']
        assert transaction.tr_type_id == transaction_types['BUY']
        
        # Cleanup
        await transaction_model.delete_transaction(transaction.tr_id)

    async def test_get_transaction(self, transaction_model, sample_sku, transaction_types):
        """Test retrieving a transaction by ID"""
        transaction_data = {
            'sku_id': sample_sku.sku_id,
            'tr_type_id': transaction_types['SELL'],
            'tr_qty': 5,
            'before_qty': sample_sku.sku_qty,
            'after_qty': sample_sku.sku_qty - 5,
            'tr_timestamp': datetime.now(),
            'description': 'Test retrieval',
            'user_id': 1
        }
        created = await transaction_model.create_transaction(transaction_data)
        
        # Test retrieval
        transaction = await transaction_model.get_transaction(created.tr_id)
        assert transaction is not None
        assert transaction.tr_id == created.tr_id
        assert transaction.sku_id == transaction_data['sku_id']
        
        # Cleanup
        await transaction_model.delete_transaction(created.tr_id)

    async def test_get_transactions_by_sku(self, transaction_model, sample_sku, transaction_types):
        """Test retrieving transactions for a specific SKU"""
        transactions = []
        tr_types = ['BUY', 'SELL', 'ADJUSTMENT_PLUS']
        
        for i, tr_type in enumerate(tr_types):
            data = {
                'sku_id': sample_sku.sku_id,
                'tr_type_id': transaction_types[tr_type],
                'tr_qty': i + 1,
                'before_qty': sample_sku.sku_qty,
                'after_qty': sample_sku.sku_qty + (i + 1),
                'tr_timestamp': datetime.now(),
                'description': f'Test transaction {i}',
                'user_id': 1
            }
            transaction = await transaction_model.create_transaction(data)
            transactions.append(transaction)

        # Test retrieval
        sku_transactions = await transaction_model.get_all_transactions(sku_id=sample_sku.sku_id)
        assert len(sku_transactions) >= 3
        assert all(t.sku_id == sample_sku.sku_id for t in sku_transactions)

        # Cleanup
        for t in transactions:
            await transaction_model.delete_transaction(t.tr_id)

    async def test_update_transaction(self, transaction_model, sample_sku, transaction_types):
        """Test updating an existing transaction"""
        initial_data = {
            'sku_id': sample_sku.sku_id,
            'tr_type_id': transaction_types['BUY'],
            'tr_qty': 5,
            'before_qty': sample_sku.sku_qty,
            'after_qty': sample_sku.sku_qty + 5,
            'tr_timestamp': datetime.now(),
            'description': 'Initial description',
            'user_id': 1
        }
        transaction = await transaction_model.create_transaction(initial_data)

        # Update the transaction
        updated_data = {
            'description': 'Updated description'
        }
        updated = await transaction_model.update_transaction(transaction.tr_id, updated_data)
        
        assert updated is not None
        assert updated.description == updated_data['description']
        # Quantity and type should remain unchanged
        assert updated.tr_qty == initial_data['tr_qty']
        assert updated.tr_type_id == initial_data['tr_type_id']
        
        # Cleanup
        await transaction_model.delete_transaction(transaction.tr_id)

    async def test_transaction_date_filtering(self, transaction_model, sample_sku, transaction_types):
        """Test filtering transactions by date range"""
        dates = [
            datetime(2023, 1, 1, 12, 0),
            datetime(2023, 6, 1, 12, 0),
            datetime(2023, 12, 31, 12, 0)
        ]
        
        transactions = []
        for tr_timestamp in dates:
            data = {
                'sku_id': sample_sku.sku_id,
                'tr_type_id': transaction_types['BUY'],
                'tr_qty': 5,
                'before_qty': sample_sku.sku_qty,
                'after_qty': sample_sku.sku_qty + 5,
                'tr_timestamp': tr_timestamp,
                'description': f'Transaction on {tr_timestamp}',
                'user_id': 1
            }
            transaction = await transaction_model.create_transaction(data)
            transactions.append(transaction)

        # Test date range filtering
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 6, 30)
        filtered = await transaction_model.get_all_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(filtered) >= 2
        assert all(start_date <= t.tr_timestamp <= end_date for t in filtered)

        # Cleanup
        for t in transactions:
            await transaction_model.delete_transaction(t.tr_id)

    async def test_transaction_pagination(self, transaction_model, sample_sku, transaction_types):
        """Test transaction pagination"""
        # Create more transactions than PAGE_SIZE
        transactions = []
        for i in range(TransactionModel.PAGE_SIZE + 5):
            data = {
                'sku_id': sample_sku.sku_id,
                'tr_type_id': transaction_types['BUY'],
                'tr_qty': i + 1,
                'before_qty': sample_sku.sku_qty,
                'after_qty': sample_sku.sku_qty + (i + 1),
                'tr_timestamp': datetime.now(),
                'description': f'Transaction {i}',
                'user_id': 1
            }
            transaction = await transaction_model.create_transaction(data)
            transactions.append(transaction)

        try:
            # Test initial load with default max_transaction_count
            await transaction_model.load_data(sample_sku.sku_id)
            initial_page_size = min(TransactionModel.PAGE_SIZE, transaction_model.max_transaction_count)
            assert len(transaction_model._data) == initial_page_size
            
            # Test can_load_more
            can_load = transaction_model.can_load_more()
            if transaction_model.max_transaction_count > TransactionModel.PAGE_SIZE:
                assert can_load
                
                # Test load_more
                more_loaded = await transaction_model.load_more()
                assert more_loaded
                assert len(transaction_model._data) > TransactionModel.PAGE_SIZE
            else:
                assert not can_load
            
            # Test with smaller max transaction count
            transaction_model.set_max_transaction_count(50)
            await transaction_model.load_data(sample_sku.sku_id)
            assert len(transaction_model._data) <= 50
            
            # Test date range filtering with pagination
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now()
            transaction_model.set_date_range(start_date, end_date)
            await transaction_model.load_data(sample_sku.sku_id)
            assert all(start_date <= t.tr_timestamp <= end_date for t in transaction_model._data)

        finally:
            # Cleanup
            for t in transactions:
                await transaction_model.delete_transaction(t.tr_id) 