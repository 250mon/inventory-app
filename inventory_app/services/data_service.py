from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date
from db.db_utils import DbUtil
from db.models import Category, Item, SKU, Transaction, TransactionType, User
from common.d_logger import Logs
from common.singleton import Singleton
from config import Config

logger = Logs().get_logger("db")

class DataService(metaclass=Singleton):
    def __init__(self):
        self.db_util = DbUtil()
        self.max_transaction_count = Config.MAX_TRANSACTION_COUNT
        self.show_inactive_items = False

    # Category operations
    async def get_categories(self) -> List[Category]:
        """Get all categories"""
        async with self.db_util.session() as session:
            result = await session.execute(select(Category))
            return result.scalars().all()

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        async with self.db_util.session() as session:
            result = await session.execute(
                select(Category).where(Category.category_id == category_id)
            )
            return result.scalar_one_or_none()

    async def create_category(self, category_data: dict) -> Category:
        async with self.db_util.session() as session:
            category = Category(**category_data)
            session.add(category)
            await session.commit()
            await session.refresh(category)
            return category

    async def update_category(self, category_id: int, category_data: dict) -> Optional[Category]:
        async with self.db_util.session() as session:
            category = await self.get_category_by_id(category_id)
            if category:
                for key, value in category_data.items():
                    setattr(category, key, value)
                await session.commit()
                await session.refresh(category)
            return category

    async def delete_category(self, category_id: int) -> bool:
        async with self.db_util.session() as session:
            category = await self.get_category_by_id(category_id)
            if category:
                await session.delete(category)
                await session.commit()
                return True
            return False

    # Item operations
    async def get_items(self, include_inactive: bool = False) -> List[Item]:
        """Get all items, optionally including inactive ones"""
        async with self.db_util.session() as session:
            query = select(Item)
            if not include_inactive:
                query = query.where(Item.active == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_item_by_id(self, item_id: int) -> Optional[Item]:
        async with self.db_util.session() as session:
            result = await session.execute(
                select(Item).where(Item.item_id == item_id)
            )
            return result.scalar_one_or_none()

    async def create_item(self, item_data: dict) -> Item:
        async with self.db_util.session() as session:
            item = Item(**item_data)
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item

    async def update_item(self, item_id: int, item_data: dict) -> Optional[Item]:
        async with self.db_util.session() as session:
            item = await self.get_item_by_id(item_id)
            if item:
                for key, value in item_data.items():
                    setattr(item, key, value)
                await session.commit()
                await session.refresh(item)
            return item

    async def delete_item(self, item_id: int) -> bool:
        async with self.db_util.session() as session:
            item = await self.get_item_by_id(item_id)
            if item:
                await session.delete(item)
                await session.commit()
                return True
            return False

    # SKU operations
    async def get_skus(self, item_id: Optional[int] = None) -> List[SKU]:
        """Get SKUs, optionally filtered by item_id"""
        async with self.db_util.session() as session:
            query = select(SKU)
            if not self.show_inactive_items:
                query = query.join(Item).where(and_(
                    SKU.active == True,
                    Item.active == True
                ))
            if item_id:
                query = query.where(SKU.item_id == item_id)
            result = await session.execute(query)
            return result.scalars().all()

    async def get_sku_by_id(self, sku_id: int) -> Optional[SKU]:
        async with self.db_util.session() as session:
            result = await session.execute(
                select(SKU).where(SKU.sku_id == sku_id)
            )
            return result.scalar_one_or_none()

    async def create_sku(self, sku_data: dict) -> SKU:
        """Create a new SKU record
        
        Args:
            sku_data: Dictionary containing SKU data with fields:
                - item_id: ID of parent item
                - root_sku: ID of root SKU (0 if this is a root)
                - sub_name: Sub name of SKU
                - active: Active status
                - sku_qty: Current quantity
                - min_qty: Minimum quantity threshold
                - expiration_date: Expiration date
                - description: Description text
                - bit_code: Bit code value
        
        Returns:
            Newly created SKU object
        """
        async with self.db_util.session() as session:
            # Create new SKU object
            sku = SKU(**sku_data)
            session.add(sku)
            await session.commit()
            await session.refresh(sku)
            return sku

    async def update_sku(self, sku_id: int, sku_data: dict) -> Optional[SKU]:
        """Update existing SKU"""
        async with self.db_util.session() as session:
            sku = await self.get_sku_by_id(sku_id)
            if sku:
                for key, value in sku_data.items():
                    setattr(sku, key, value)
                await session.commit()
                await session.refresh(sku)
            return sku

    async def delete_sku(self, sku_id: int) -> bool:
        """Delete SKU by id"""
        async with self.db_util.session() as session:
            sku = await self.get_sku_by_id(sku_id)
            if sku:
                await session.delete(sku)
                await session.commit()
                return True
            return False

    # Transaction operations
    async def get_transactions(
        self, 
        sku_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        async with self.db_util.session() as session:
            query = select(Transaction)
            
            if not self.show_inactive_items:
                query = query.join(SKU).join(Item).where(and_(
                    SKU.active == True,
                    Item.active == True
                ))

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)
            
            if start_date and end_date:
                query = query.where(and_(
                    Transaction.tr_timestamp >= start_date,
                    Transaction.tr_timestamp <= end_date
                ))

            query = query.order_by(Transaction.tr_id.desc())
            query = query.limit(self.max_transaction_count)
            
            result = await session.execute(query)
            return result.scalars().all()

    async def create_transaction(self, transaction_data: dict) -> Transaction:
        async with self.db_util.session() as session:
            transaction = Transaction(**transaction_data)
            session.add(transaction)
            await session.commit()
            await session.refresh(transaction)
            return transaction

    async def update_transaction(self, tr_id: int, tr_data: dict) -> Optional[Transaction]:
        """Update existing transaction"""
        async with self.db_util.session() as session:
            transaction = await self.get_transaction_by_id(tr_id)
            if transaction:
                for key, value in tr_data.items():
                    setattr(transaction, key, value)
                await session.commit()
                await session.refresh(transaction)
            return transaction

    async def delete_transaction(self, tr_id: int) -> bool:
        """Delete transaction by id"""
        async with self.db_util.session() as session:
            transaction = await self.get_transaction_by_id(tr_id)
            if transaction:
                await session.delete(transaction)
                await session.commit()
                return True
            return False

    async def get_transaction_by_id(self, tr_id: int) -> Optional[Transaction]:
        """Get transaction by id"""
        async with self.db_util.session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.tr_id == tr_id)
            )
            return result.scalar_one_or_none()

    # Reference data operations
    async def get_transaction_types(self) -> List[TransactionType]:
        async with self.db_util.session() as session:
            result = await session.execute(select(TransactionType))
            return result.scalars().all()

    async def get_users(self) -> List[User]:
        async with self.db_util.session() as session:
            result = await session.execute(select(User))
            return result.scalars().all()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        async with self.db_util.session() as session:
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def get_user_by_name(self, username: str) -> Optional[User]:
        async with self.db_util.session() as session:
            result = await session.execute(
                select(User).where(User.user_name == username)
            )
            return result.scalar_one_or_none()

    async def create_user(self, user_data: dict) -> User:
        async with self.db_util.session() as session:
            user = User(**user_data)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        async with self.db_util.session() as session:
            user = await self.get_user_by_id(user_id)
            if user:
                for key, value in user_data.items():
                    setattr(user, key, value)
                await session.commit()
                await session.refresh(user)
            return user

    async def delete_user(self, user_id: int) -> bool:
        async with self.db_util.session() as session:
            user = await self.get_user_by_id(user_id)
            if user:
                await session.delete(user)
                await session.commit()
                return True
            return False

    def set_max_transaction_count(self, count: int):
        if count > 0:
            self.max_transaction_count = count
        else:
            logger.warn(f"count({count}) is not a positive integer")

    def toggle_show_inactive(self):
        self.show_inactive_items = not self.show_inactive_items 