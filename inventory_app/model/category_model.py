from PySide6.QtCore import Signal
from sqlalchemy import select
from typing import List, Dict, Optional
from model.sql_model import SQLTableModel
from model.base_model import BaseDBModel
from model.models import Category
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")

class CategoryModel(SQLTableModel, BaseDBModel):
    category_model_changed_signal = Signal(object)
    
    def __init__(self):
        super().__init__()
        self._setup_model()
        
    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = ['category_id', 'category_name', 'description']
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'category_id': Config.EditLevel.NotEditable,
            'category_name': Config.EditLevel.AdminModifiable,
            'description': Config.EditLevel.UserModifiable
        }

    # CRUD Operations
    async def create_category(self, category_data: dict) -> Category:
        """Create a new category in the database"""
        async with self.session() as session:
            category = Category(**category_data)
            session.add(category)
            await session.flush()  # Flush to get the ID
            await session.refresh(category)
            return category

    async def get_category(self, category_id: int) -> Optional[Category]:
        """Get a category by ID"""
        async with self.session() as session:
            return await session.get(Category, category_id)

    async def get_category_by_name(self, name: str) -> Optional[Category]:
        """Get a category by name"""
        async with self.session() as session:
            result = await session.execute(
                select(Category).where(Category.category_name == name)
            )
            return result.scalar_one_or_none()

    async def get_all_categories(self) -> List[Category]:
        """Get all categories"""
        async with self.session() as session:
            result = await session.execute(select(Category))
            return result.scalars().all()

    async def update_category(self, category_id: int, category_data: dict) -> Optional[Category]:
        """Update an existing category"""
        async with self.session() as session:
            category = await session.get(Category, category_id)
            if category:
                for key, value in category_data.items():
                    setattr(category, key, value)
                await session.flush()
                await session.refresh(category)
                return category
            return None

    async def delete_category(self, category_id: int) -> bool:
        """Delete a category"""
        async with self.session() as session:
            category = await session.get(Category, category_id)
            if category:
                await session.delete(category)
                return True
            return False

    # Qt Model Methods
    async def load_data(self):
        """Load categories for the Qt model"""
        self._data = await self.get_all_categories()
        self.layoutChanged.emit()
        
    def get_category_names(self) -> List[str]:
        """Get list of category names for UI"""
        return [cat.category_name for cat in self._data]

    def validate_category(self, category_name: str, exclude_id: Optional[int] = None) -> bool:
        """Validate category data"""
        if not category_name:
            return False
            
        # Check for duplicate category names
        return not any(cat.category_name == category_name 
                      for cat in self._data 
                      if cat.category_id != exclude_id)

    def create_empty_category(self) -> Category:
        """Create a new empty category object"""
        return Category(
            category_id=0,  # Temporary ID
            category_name='',
        )