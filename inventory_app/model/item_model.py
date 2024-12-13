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
            'item_id', 'active', 'item_name', 'category_name',
            'description', 'category_id'
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'item_id': Config.EditLevel.NotEditable,
            'active': Config.EditLevel.AdminModifiable,
            'item_name': Config.EditLevel.AdminModifiable,
            'category_name': Config.EditLevel.UserModifiable,
            'description': Config.EditLevel.UserModifiable,
            'category_id': Config.EditLevel.NotEditable
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
            result = await session.execute(
                select(Item).where(Item.item_name == name)
            )
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
        return not any(item.item_name == item_name 
                      for item in self._data 
                      if item.item_id != exclude_id)

    def create_empty_item(self) -> Item:
        """Create a new empty item object"""
        return Item(
            item_id=0,  # Temporary ID
            active=True,
            item_name='',
            category_id=0,
            description=''
        )

    def is_active_row(self, index: int) -> bool:
        """Check if row is active"""
        if 0 <= index < len(self._data):
            return bool(self._data[index].active)
        return False

    def get_user_privilege(self) -> Config.UserPrivilege:
        """Get user privilege level"""
        return Config.UserPrivilege.Admin if self.user_name == "admin" else Config.UserPrivilege.User
