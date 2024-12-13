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
            'sku_id', 'root_sku', 'item_name', 'sub_name',
            'active', 'sku_qty', 'min_qty', 'expiration_date',
            'description', 'bit_code', 'sku_name', 'item_id'
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'sku_id': Config.EditLevel.NotEditable,
            'root_sku': Config.EditLevel.Creatable,
            'item_name': Config.EditLevel.NotEditable,
            'sub_name': Config.EditLevel.UserModifiable,
            'active': Config.EditLevel.AdminModifiable,
            'sku_qty': Config.EditLevel.AdminModifiable,
            'min_qty': Config.EditLevel.UserModifiable,
            'expiration_date': Config.EditLevel.Creatable,
            'description': Config.EditLevel.UserModifiable,
            'bit_code': Config.EditLevel.AdminModifiable,
            'sku_name': Config.EditLevel.NotEditable,
            'item_id': Config.EditLevel.NotEditable
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
                select(SKU)
                .join(SKU.item)
                .options(selectinload(SKU.item))
                .where(SKU.sku_id == sku_id)
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_all_skus(self, item_id: Optional[int] = None) -> List[SKU]:
        """Get all SKUs, optionally filtered by item_id"""
        async with self.session() as session:
            # Eager load item
            query = (
                select(SKU)
                .join(SKU.item)
                .options(selectinload(SKU.item))
            )
            if not self.show_inactive_items:
                query = query.where(and_(
                    SKU.active == True,
                    Item.active == True
                ))
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
            setattr(sku, 'sku_name', f"{sku.item.item_name} {sku.sub_name}".strip())

    async def validate_sku(self, root_sku: int, item_id: int) -> bool:
        """Validate SKU data"""
        if root_sku == 0:
            return True  # No root SKU to validate

        async with self.session() as session:
            # Validate root SKU exists and belongs to the same item in a single query
            query = select(SKU).where(
                SKU.sku_id == root_sku,
                SKU.item_id == item_id
            )
            result = await session.execute(query)
            root = result.scalar_one_or_none()

            return root is not None

    def create_empty_sku(self) -> SKU:
        """Create a new empty SKU object"""
        return SKU(
            sku_id=0,  # Temporary ID
            root_sku=0,
            active=True,
            sub_name='',
            sku_qty=0,
            min_qty=Config.DEFAULT_MIN_QTY,
            item_id=0,
            description='',
            bit_code=''
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
            result = await session.execute(
                select(SKU).where(SKU.root_sku == sku_id)
            )
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
            query = (
                select(SKU)
                .join(SKU.item)
                .options(selectinload(SKU.item))
            )
            
            if not self.show_inactive_items:
                query = query.where(and_(
                    SKU.active == True,
                    Item.active == True
                ))
            
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
                query = query.join(Item).where(and_(
                    SKU.active == True,
                    Item.active == True
                ))

            if item_id:
                query = query.where(SKU.item_id == item_id)

            # Convert the query to a subquery to avoid the deprecation warning
            subquery = query.subquery()

            # Use the subquery in the select statement
            result = await session.execute(select(func.count()).select_from(subquery))
            return result.scalar()