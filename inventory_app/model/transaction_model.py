from datetime import datetime
from typing import List, Optional

from common.d_logger import Logs
from config import Config
from model.base_model import BaseDBModel
from model.models import SKU, Item, Transaction, TransactionType
from model.sql_model import SQLTableModel
from PySide6.QtCore import Signal
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

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
            # Eager load related tables
            query = (
                select(Transaction)
                .join(Transaction.sku)
                .join(SKU.item)
                .options(joinedload(Transaction.sku).joinedload(SKU.item))
            )
            return await session.scalar(query.where(Transaction.tr_id == tr_id))

    async def get_all_transactions(
        self,
        sku_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Transaction]:
        """Get all transactions with optional filters"""
        async with self.session() as session:
            # Eager load related tables
            query = (
                select(Transaction)
                .join(Transaction.sku)
                .join(SKU.item)
                .options(joinedload(Transaction.sku).joinedload(SKU.item))
            )

            if not self.show_inactive_items:
                query = query.where(and_(SKU.active == True, Item.active == True))

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)

            if start_date:
                query = query.where(Transaction.tr_timestamp >= start_date)
            if end_date:
                query = query.where(Transaction.tr_timestamp <= end_date)

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
            # Eager load related tables
            query = (
                select(Transaction)
                .join(Transaction.sku)
                .join(SKU.item)
                .options(joinedload(Transaction.sku).joinedload(SKU.item))
            )

            if not self.show_inactive_items:
                query = query.where(and_(SKU.active == True, Item.active == True))

            if sku_id:
                query = query.where(Transaction.sku_id == sku_id)

            if self.beg_timestamp:
                query = query.where(Transaction.tr_timestamp >= self.beg_timestamp)
            if self.end_timestamp:
                query = query.where(Transaction.tr_timestamp <= self.end_timestamp)

            # Add ordering to ensure consistent pagination
            query = query.order_by(Transaction.tr_id.desc())

            # Add pagination
            accumulated_count = page * self.PAGE_SIZE
            remaining_count = self.max_transaction_count - accumulated_count
            max_count = min(remaining_count, self.PAGE_SIZE)
            query = query.offset(accumulated_count).limit(max_count)

            result = await session.execute(query)
            return result.scalars().all()

    async def get_total_records(self, sku_id: Optional[int] = None) -> int:
        """Get total number of records"""
        async with self.session() as session:
            query = select(func.count(Transaction.tr_id))

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
        if start_date > end_date:
            logger.error("start_date cannot be after end_date")
            raise ValueError("start_date cannot be after end_date")
        self.beg_timestamp = start_date
        self.end_timestamp = end_date

    def clear_date_range(self):
        """Clear the date range filter"""
        self.beg_timestamp = None
        self.end_timestamp = None

    def validate_transaction(self, tr_type_id: int, tr_qty: int) -> bool:
        """Validate transaction data"""
        if tr_qty == 0:
            return False  # Quantity cannot be zero
        if (
            tr_type_id in [TransactionType.BUY, TransactionType.ADJUSTMENT_PLUS]
            and tr_qty < 0
        ):
            return False  # Positive quantity required
        if (
            tr_type_id in [TransactionType.SELL, TransactionType.ADJUSTMENT_MINUS]
            and tr_qty > 0
        ):
            return False  # Negative quantity required
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