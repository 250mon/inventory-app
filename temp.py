# models.py
from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import event
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


class Category(Base):
    __tablename__ = "category"

    category_id = Column(Integer, primary_key=True)
    category_name = Column(Text, nullable=False, unique=True)

    items = relationship(
        "Item", back_populates="category", cascade="all, delete-orphan"
    )


class Item(Base):
    __tablename__ = "items"

    item_id = Column(Integer, primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    item_name = Column(Text, nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey("category.category_id"), nullable=False)
    description = Column(Text)

    category = relationship("Category", back_populates="items")
    skus = relationship("SKU", back_populates="item", cascade="all, delete-orphan")


class SKU(Base):
    __tablename__ = "skus"

    sku_id = Column(Integer, primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    root_sku = Column(Integer, nullable=False, default=0)
    sub_name = Column(Text)
    bit_code = Column(Text)
    sku_qty = Column(Integer, nullable=False)
    min_qty = Column(Integer, nullable=False, default=2)
    item_id = Column(Integer, ForeignKey("items.item_id"), nullable=False)
    expiration_date = Column(Date, nullable=False, default=date(9999, 1, 1))
    description = Column(Text)

    item = relationship("Item", back_populates="skus")
    transactions = relationship(
        "Transaction", back_populates="sku", cascade="all, delete-orphan"
    )


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    user_name = Column(Text, nullable=False, unique=True)
    user_password = Column(String, nullable=False)

    transactions = relationship("Transaction", back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash"""
        return check_password_hash(self.user_password, password)


# SQLAlchemy event listener to hash password before insert/update
@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def hash_password(mapper, connection, target):
    """Hash password before saving to database"""
    if target.user_password and not target.user_password.startswith("pbkdf2:sha256:"):
        target.user_password = generate_password_hash(target.user_password)


class TransactionType(Base):
    __tablename__ = "transaction_type"

    tr_type_id = Column(Integer, primary_key=True)
    tr_type = Column(Text, nullable=False, unique=True)

    transactions = relationship("Transaction", back_populates="transaction_type")

    # Define constants for transaction types
    BUY = 1
    SELL = 2
    ADJUSTMENT_PLUS = 3
    ADJUSTMENT_MINUS = 4

    # Map IDs to type names
    TYPE_NAMES = {
        BUY: "Buy",
        SELL: "Sell",
        ADJUSTMENT_PLUS: "Adjustment+",
        ADJUSTMENT_MINUS: "Adjustment-",
    }

    @classmethod
    def get_type_name(cls, type_id: int) -> str:
        """Get the name of a transaction type by ID"""
        return cls.TYPE_NAMES.get(type_id, "Unknown")

    @classmethod
    def is_valid_type(cls, type_id: int) -> bool:
        """Check if a transaction type ID is valid"""
        return type_id in cls.TYPE_NAMES


class Transaction(Base):
    __tablename__ = "transactions"

    tr_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sku_id = Column(Integer, ForeignKey("skus.sku_id"), nullable=False)
    tr_type_id = Column(
        Integer, ForeignKey("transaction_type.tr_type_id"), nullable=False
    )
    tr_qty = Column(Integer, nullable=False)
    before_qty = Column(Integer, nullable=False)
    after_qty = Column(Integer, nullable=False)
    tr_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(Text)

    user = relationship("User", back_populates="transactions")
    sku = relationship("SKU", back_populates="transactions")
    transaction_type = relationship("TransactionType", back_populates="transactions")

    @property
    def tr_type_name(self) -> str:
        """Get the name of the transaction type"""
        return TransactionType.get_type_name(self.tr_type_id)

    def validate_quantities(self) -> bool:
        """Validate that before_qty and after_qty are consistent with tr_qty"""
        if (
            self.tr_type_id == TransactionType.BUY
            or self.tr_type_id == TransactionType.ADJUSTMENT_PLUS
        ):
            return self.after_qty == self.before_qty + self.tr_qty
        elif (
            self.tr_type_id == TransactionType.SELL
            or self.tr_type_id == TransactionType.ADJUSTMENT_MINUS
        ):
            return self.after_qty == self.before_qty - self.tr_qty
        return False


# base_model.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import Config
from common.d_logger import Logs
from contextlib import asynccontextmanager
from model.models import Base

logger = Logs().get_logger("main")


class BaseDBModel:
    """Base class for database models providing SQLAlchemy connection handling"""

    _engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:", echo=False, future=True
    )

    _async_session = sessionmaker(
        class_=AsyncSession, expire_on_commit=False, bind=_engine
    )

    @classmethod
    @asynccontextmanager
    async def session(cls):
        """Provides a session context manager that automatically handles commit/rollback"""
        session = cls._async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            await session.close()

    @classmethod
    async def create_tables(cls):
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def drop_tables(cls):
        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# item_model.py
from PySide6.QtCore import Signal
from sqlalchemy import select
from typing import List, Optional
from model.sql_model import SQLTableModel
from model.base_model import BaseDBModel
from model.models import Item
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")


class ItemModel(SQLTableModel, BaseDBModel):
    item_model_changed_signal = Signal(object)

    def __init__(self, user_name: str):
        super().__init__()
        self.user_name = user_name
        self._setup_model()

    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = [
            "item_id",
            "active",
            "item_name",
            "category_name",
            "description",
            "category_id",
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}

        self.col_edit_lvl = {
            "item_id": Config.EditLevel.NotEditable,
            "active": Config.EditLevel.AdminModifiable,
            "item_name": Config.EditLevel.AdminModifiable,
            "category_name": Config.EditLevel.UserModifiable,
            "description": Config.EditLevel.UserModifiable,
            "category_id": Config.EditLevel.NotEditable,
        }

    # CRUD Operations
    async def create_item(self, item_data: dict) -> Item:
        """Create a new item in the database"""
        async with self.session() as session:
            item = Item(**item_data)
            session.add(item)
            await session.flush()
            await session.refresh(item)
            return item

    async def get_item(self, item_id: int) -> Optional[Item]:
        """Get an item by ID"""
        async with self.session() as session:
            return await session.get(Item, item_id)

    async def get_item_by_name(self, name: str) -> Optional[Item]:
        """Get an item by name"""
        async with self.session() as session:
            result = await session.execute(select(Item).where(Item.item_name == name))
            return result.scalar_one_or_none()

    async def get_all_items(self, include_inactive: bool = False) -> List[Item]:
        """Get all items, optionally including inactive ones"""
        async with self.session() as session:
            query = select(Item)
            if not include_inactive:
                query = query.where(Item.active == True)
            result = await session.execute(query)
            return result.scalars().all()

    async def update_item(self, item_id: int, item_data: dict) -> Optional[Item]:
        """Update an existing item"""
        async with self.session() as session:
            item = await session.get(Item, item_id)
            if item:
                for key, value in item_data.items():
                    setattr(item, key, value)
                await session.flush()
                await session.refresh(item)
                return item
            return None

    async def delete_item(self, item_id: int) -> bool:
        """Delete an item"""
        async with self.session() as session:
            item = await session.get(Item, item_id)
            if item:
                await session.delete(item)
                return True
            return False

    # Qt Model Methods
    async def load_data(self, include_inactive: bool = False):
        """Load items for the Qt model"""
        self._data = await self.get_all_items(include_inactive)
        self.layoutChanged.emit()

    def validate_item(self, item_name: str, exclude_id: Optional[int] = None) -> bool:
        """Validate item data"""
        if not item_name:
            return False

        # Check for duplicate item names
        return not any(
            item.item_name == item_name
            for item in self._data
            if item.item_id != exclude_id
        )

    def create_empty_item(self) -> Item:
        """Create a new empty item object"""
        return Item(
            item_id=0,  # Temporary ID
            active=True,
            item_name="",
            category_id=0,
            description="",
        )

    def is_active_row(self, index: int) -> bool:
        """Check if row is active"""
        if 0 <= index < len(self._data):
            return bool(self._data[index].active)
        return False

    def get_user_privilege(self) -> Config.UserPrivilege:
        """Get user privilege level"""
        return (
            Config.UserPrivilege.Admin
            if self.user_name == "admin"
            else Config.UserPrivilege.User
        )


# sku_model.py
from PySide6.QtCore import Signal
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from model.sql_model import SQLTableModel
from model.base_model import BaseDBModel
from model.models import SKU, Item
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")


class SkuModel(SQLTableModel, BaseDBModel):
    sku_model_changed_signal = Signal(object)
    PAGE_SIZE = 100  # Number of records to load at once

    def __init__(self):
        super().__init__()
        self._setup_model()
        self.show_inactive_items = False
        self._current_page = 0
        self._total_records = 0
        self._current_item_id = None
        self._data = []

    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = [
            "sku_id",
            "root_sku",
            "item_name",
            "sub_name",
            "active",
            "sku_qty",
            "min_qty",
            "expiration_date",
            "description",
            "bit_code",
            "sku_name",
            "item_id",
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}

        self.col_edit_lvl = {
            "sku_id": Config.EditLevel.NotEditable,
            "root_sku": Config.EditLevel.Creatable,
            "item_name": Config.EditLevel.NotEditable,
            "sub_name": Config.EditLevel.UserModifiable,
            "active": Config.EditLevel.AdminModifiable,
            "sku_qty": Config.EditLevel.AdminModifiable,
            "min_qty": Config.EditLevel.UserModifiable,
            "expiration_date": Config.EditLevel.Creatable,
            "description": Config.EditLevel.UserModifiable,
            "bit_code": Config.EditLevel.AdminModifiable,
            "sku_name": Config.EditLevel.NotEditable,
            "item_id": Config.EditLevel.NotEditable,
        }

    # CRUD Operations
    async def create_sku(self, sku_data: dict) -> SKU:
        """Create a new SKU in the database"""
        async with self.session() as session:
            sku = SKU(**sku_data)
            session.add(sku)
            await session.flush()
            await session.refresh(sku)
            return sku

    async def get_sku(self, sku_id: int) -> Optional[SKU]:
        """Get a SKU by ID with eager loading"""
        async with self.session() as session:
            # Eager load item
            query = (
                select(SKU).options(selectinload(SKU.item)).where(SKU.sku_id == sku_id)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_all_skus(self, item_id: Optional[int] = None) -> List[SKU]:
        """Get all SKUs, optionally filtered by item_id"""
        async with self.session() as session:
            # Eager load item
            query = select(SKU).options(selectinload(SKU.item))
            if not self.show_inactive_items:
                query = query.where(and_(SKU.active == True, Item.active == True))
            if item_id:
                query = query.where(SKU.item_id == item_id)
            result = await session.execute(query)
            return result.scalars().all()

    async def update_sku(self, sku_id: int, sku_data: dict) -> Optional[SKU]:
        """Update an existing SKU"""
        async with self.session() as session:
            sku = await session.get(SKU, sku_id)
            if sku:
                for key, value in sku_data.items():
                    setattr(sku, key, value)
                await session.flush()
                await session.refresh(sku)
                return sku
            return None

    async def delete_sku(self, sku_id: int) -> bool:
        """Delete a SKU"""
        async with self.session() as session:
            sku = await session.get(SKU, sku_id)
            if sku:
                await session.delete(sku)
                return True
            return False

    # Qt Model Methods
    async def load_data(self, item_id: Optional[int] = None):
        """Load SKUs for the Qt model"""
        self._current_item_id = item_id
        self._current_page = 0
        self._total_records = await self.get_total_records(item_id)
        self._data = await self.get_page(0, item_id)
        self._update_sku_names()
        self.layoutChanged.emit()

    async def load_more(self):
        """Load next page of data"""
        if len(self._data) < self._total_records:
            self._current_page += 1
            new_data = await self.get_page(self._current_page, self._current_item_id)
            if new_data:
                self._data.extend(new_data)
                self._update_sku_names()
                self.layoutChanged.emit()
                return True
        return False

    def can_load_more(self) -> bool:
        """Check if more data can be loaded"""
        return len(self._data) < self._total_records

    def _update_sku_names(self):
        """Update SKU names using item names"""
        for sku in self._data:
            setattr(sku, "sku_name", f"{sku.item.item_name} {sku.sub_name}".strip())

    async def validate_sku(self, root_sku: int, item_id: int) -> bool:
        """Validate SKU data"""
        if root_sku == 0:
            return True  # No root SKU to validate

        async with self.session() as session:
            # Validate root SKU exists and belongs to the same item in a single query
            query = select(SKU).where(SKU.sku_id == root_sku, SKU.item_id == item_id)
            result = await session.execute(query)
            root = result.scalar_one_or_none()

            return root is not None

    def create_empty_sku(self) -> SKU:
        """Create a new empty SKU object"""
        return SKU(
            sku_id=0,  # Temporary ID
            root_sku=0,
            active=True,
            sub_name="",
            sku_qty=0,
            min_qty=Config.DEFAULT_MIN_QTY,
            item_id=0,
            description="",
            bit_code="",
        )

    def is_active_row(self, index: int) -> bool:
        """Check if row is active"""
        if 0 <= index < len(self._data):
            return bool(self._data[index].active and self._data[index].item.active)
        return False

    async def is_sku_qty_correct(self, sku_id: int, sku_qty: int) -> bool:
        """Check if SKU quantity is correct for root SKU"""
        async with self.session() as session:
            # Get all sub-SKUs directly from database
            result = await session.execute(select(SKU).where(SKU.root_sku == sku_id))
            sub_skus = result.scalars().all()

            if not sub_skus:
                return True

            return sku_qty == sum(sku.sku_qty for sku in sub_skus)

    def toggle_show_inactive(self):
        """Toggle showing inactive items"""
        self.show_inactive_items = not self.show_inactive_items

    async def get_page(self, page: int, item_id: Optional[int] = None) -> List[SKU]:
        """Get a page of SKUs"""
        async with self.session() as session:
            # Eager load item
            query = select(SKU).options(selectinload(SKU.item))

            if not self.show_inactive_items:
                query = query.join(Item).where(
                    and_(SKU.active == True, Item.active == True)
                )

            if item_id:
                query = query.where(SKU.item_id == item_id)

            # Add ordering to ensure consistent pagination
            query = query.order_by(SKU.sku_id)

            # Add pagination
            query = query.offset(page * self.PAGE_SIZE).limit(self.PAGE_SIZE)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_total_records(self, item_id: Optional[int] = None) -> int:
        """Get total number of records"""
        async with self.session() as session:
            query = select(SKU)

            if not self.show_inactive_items:
                query = query.join(Item).where(
                    and_(SKU.active == True, Item.active == True)
                )

            if item_id:
                query = query.where(SKU.item_id == item_id)

            result = await session.execute(select(func.count()).select_from(query))
            return result.scalar()


# transaction_model.py
from PySide6.QtCore import Signal
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime
from model.sql_model import SQLTableModel
from model.base_model import BaseDBModel
from model.models import Transaction, SKU, Item
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")


class TransactionModel(SQLTableModel, BaseDBModel):
    transaction_model_changed_signal = Signal(object)
    PAGE_SIZE = 100  # Number of records to load at once

    def __init__(self):
        super().__init__()
        self._setup_model()
        self.show_inactive_items = False
        self.max_transaction_count = Config.MAX_TRANSACTION_COUNT
        self.beg_timestamp = None
        self.end_timestamp = None
        self.current_sku_id = None
        self._current_page = 0
        self._total_records = 0

    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = [
            "tr_id",
            "sku_id",
            "tr_type",
            "tr_qty",
            "before_qty",
            "after_qty",
            "tr_timestamp",
            "description",
            "user_name",
            "tr_type_id",
            "user_id",
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}

        self.col_edit_lvl = {
            "tr_id": Config.EditLevel.NotEditable,
            "sku_id": Config.EditLevel.NotEditable,
            "tr_type": Config.EditLevel.Creatable,
            "tr_qty": Config.EditLevel.Creatable,
            "before_qty": Config.EditLevel.NotEditable,
            "after_qty": Config.EditLevel.NotEditable,
            "tr_timestamp": Config.EditLevel.NotEditable,
            "description": Config.EditLevel.UserModifiable,
            "user_name": Config.EditLevel.NotEditable,
            "tr_type_id": Config.EditLevel.NotEditable,
            "user_id": Config.EditLevel.NotEditable,
        }

    # CRUD Operations
    async def create_transaction(self, tr_data: dict) -> Transaction:
        """Create a new transaction in the database"""
        async with self.session() as session:
            # Set default values
            tr_data.setdefault("tr_timestamp", datetime.now())
            tr_data.setdefault("description", "")

            transaction = Transaction(**tr_data)
            session.add(transaction)
            await session.flush()
            await session.refresh(transaction)
            return transaction

    async def get_transaction(self, tr_id: int) -> Optional[Transaction]:
        """Get a transaction by ID"""
        async with self.session() as session:
            return await session.get(Transaction, tr_id)

    async def get_all_transactions(
        self,
        sku_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Transaction]:
        """Get all transactions with optional filters"""
        async with self.session() as session:
            query = select(Transaction)

            if not self.show_inactive_items:
                query = (
                    query.join(SKU)
                    .join(Item)
                    .where(and_(SKU.active == True, Item.active == True))
                )

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)

            if start_date and end_date:
                query = query.where(
                    and_(
                        Transaction.tr_timestamp >= start_date,
                        Transaction.tr_timestamp <= end_date,
                    )
                )

            query = query.order_by(Transaction.tr_id.desc())
            query = query.limit(self.max_transaction_count)

            result = await session.execute(query)
            return result.scalars().all()

    async def update_transaction(
        self, tr_id: int, tr_data: dict
    ) -> Optional[Transaction]:
        """Update an existing transaction"""
        async with self.session() as session:
            transaction = await session.get(Transaction, tr_id)
            if transaction:
                for key, value in tr_data.items():
                    setattr(transaction, key, value)
                await session.flush()
                await session.refresh(transaction)
                return transaction
            return None

    async def delete_transaction(self, tr_id: int) -> bool:
        """Delete a transaction"""
        async with self.session() as session:
            transaction = await session.get(Transaction, tr_id)
            if transaction:
                await session.delete(transaction)
                return True
            return False

    async def get_page(
        self, page: int, sku_id: Optional[int] = None
    ) -> List[Transaction]:
        """Get a page of transactions"""
        async with self.session() as session:
            query = select(Transaction)

            if not self.show_inactive_items:
                query = (
                    query.join(SKU)
                    .join(Item)
                    .where(and_(SKU.active == True, Item.active == True))
                )

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)

            if self.beg_timestamp and self.end_timestamp:
                query = query.where(
                    and_(
                        Transaction.tr_timestamp >= self.beg_timestamp,
                        Transaction.tr_timestamp <= self.end_timestamp,
                    )
                )

            # Add ordering to ensure consistent pagination
            query = query.order_by(Transaction.tr_id.desc())
            query = query.limit(self.max_transaction_count)

            # Add pagination
            query = query.offset(page * self.PAGE_SIZE).limit(self.PAGE_SIZE)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_total_records(self, sku_id: Optional[int] = None) -> int:
        """Get total number of records"""
        async with self.session() as session:
            query = select(func.count()).select_from(Transaction)

            if not self.show_inactive_items:
                query = (
                    query.join(SKU)
                    .join(Item)
                    .where(and_(SKU.active == True, Item.active == True))
                )

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)

            if self.beg_timestamp and self.end_timestamp:
                query = query.where(
                    and_(
                        Transaction.tr_timestamp >= self.beg_timestamp,
                        Transaction.tr_timestamp <= self.end_timestamp,
                    )
                )

            result = await session.execute(query)
            return result.scalar()

    async def load_data(self, sku_id: Optional[int] = None):
        """Load transactions for the Qt model"""
        self.current_sku_id = sku_id
        self._current_page = 0
        self._total_records = await self.get_total_records(sku_id)
        self._data = await self.get_page(0, sku_id)
        logger.debug(
            f"len(self._data) = {len(self._data)}, self._total_records = {self._total_records}"
        )
        self.layoutChanged.emit()

    async def load_more(self) -> bool:
        """Load next page of data"""
        if len(self._data) < self._total_records:
            self._current_page += 1
            new_data = await self.get_page(self._current_page, self.current_sku_id)
            if new_data:
                self._data.extend(new_data)
                self.layoutChanged.emit()
                return True
        return False

    def can_load_more(self) -> bool:
        """Check if more data can be loaded"""
        return len(self._data) < self._total_records

    def set_date_range(self, start_date: datetime, end_date: datetime):
        """Set the date range for filtering transactions"""
        self.beg_timestamp = start_date
        self.end_timestamp = end_date

    def clear_date_range(self):
        """Clear the date range filter"""
        self.beg_timestamp = None
        self.end_timestamp = None

    def validate_transaction(self, tr_type: str, tr_qty: int) -> bool:
        """Validate transaction data"""
        if not tr_type or tr_qty <= 0:
            return False
        return True

    def create_empty_transaction(self) -> Transaction:
        """Create a new empty transaction object"""
        return Transaction(
            tr_id=0,  # Temporary ID
            sku_id=0,
            tr_type_id=0,
            tr_qty=0,
            before_qty=0,
            after_qty=0,
            tr_timestamp=datetime.now(),
            description="",
            user_id=0,
        )

    def set_max_transaction_count(self, count: int):
        """Set maximum number of transactions to load"""
        if count > 0:
            self.max_transaction_count = count
        else:
            logger.warn(f"count({count}) is not a positive integer")

    def toggle_show_inactive(self):
        """Toggle showing inactive items"""
        self.show_inactive_items = not self.show_inactive_items
