from typing import List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from PySide6.QtCore import Qt, QModelIndex, Signal
from db.models import Item, Category
from model.sql_model import SQLTableModel
from constants import EditLevel, RowFlags
from common.d_logger import Logs

logger = Logs().get_logger("main")

class ItemSQLModel(SQLTableModel):
    """SQLAlchemy-based model for Items table"""
    
    item_changed = Signal(list)  # Emits list of changed item IDs
    
    def __init__(self, session: AsyncSession, user_name: str):
        super().__init__(session, user_name)
        self.init_params()
        
    def init_params(self):
        """Initialize model parameters"""
        self._headers = [
            'item_id', 'active', 'item_name', 'category_name',
            'description', 'category_id'
        ]
        self._column_map = {name: idx for idx, name in enumerate(self._headers)}
        
        # Column edit levels
        self.col_edit_levels = {
            'item_id': EditLevel.NotEditable,
            'active': EditLevel.AdminModifiable,
            'item_name': EditLevel.AdminModifiable,
            'category_name': EditLevel.UserModifiable,
            'description': EditLevel.UserModifiable,
            'category_id': EditLevel.NotEditable
        }
        
    async def load_data(self):
        """Load items and related category data"""
        self.beginResetModel()
        
        # Query items with categories
        stmt = select(Item, Category).join(Category)
        if not self.show_inactive:
            stmt = stmt.where(Item.active == True)
            
        result = await self.session.execute(stmt)
        self._data = [{"item": item, "category": cat} for item, cat in result]
        
        self.endResetModel()
        
    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> Optional[str]:
        if not index.isValid():
            return None
            
        row = self._data[index.row()]
        col = self._headers[index.column()]
        
        if role in (Qt.DisplayRole, Qt.EditRole, self.SortRole):
            if col == 'item_id':
                return str(row["item"].item_id)
            elif col == 'active':
                return 'Y' if row["item"].active else 'N'
            elif col == 'item_name':
                return row["item"].item_name
            elif col == 'category_name':
                return row["category"].category_name
            elif col == 'description':
                return row["item"].description or ''
            elif col == 'category_id':
                return str(row["item"].category_id)
                
        elif role == Qt.TextAlignmentRole:
            if col in ('description',):
                return Qt.AlignLeft
            return Qt.AlignCenter
            
        return None
        
    def setData(self, index: QModelIndex, value: str, role=Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
            
        row = self._data[index.row()]
        col = self._headers[index.column()]
        
        try:
            if col == 'active':
                row["item"].active = (value == 'Y')
            elif col == 'item_name':
                row["item"].item_name = value
            elif col == 'category_name':
                # Find category by name
                stmt = select(Category).where(Category.category_name == value)
                category = await self.session.execute(stmt)
                category = category.scalar_one()
                row["item"].category_id = category.category_id
                row["category"] = category
            elif col == 'description':
                row["item"].description = value
            else:
                return False
                
            self.changed_rows.add(index.row())
            self.dataChanged.emit(index, index)
            return True
            
        except Exception as e:
            logger.error(f"Error setting data: {e}")
            return False
            
    async def save_changes(self):
        """Save all changes to database"""
        try:
            # Handle deleted rows
            for row_idx in self.deleted_rows:
                item = self._data[row_idx]["item"]
                await self.session.delete(item)
                
            # Handle new and modified rows
            for row_idx in self.new_rows | self.changed_rows:
                item = self._data[row_idx]["item"]
                self.session.add(item)
                
            await self.session.commit()
            
            # Clear change tracking sets
            self.new_rows.clear()
            self.changed_rows.clear()
            self.deleted_rows.clear()
            
            # Reload data
            await self.load_data()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving changes: {e}")
            await self.session.rollback()
            return False
            
    def add_new_row(self):
        """Add new empty item row"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data))
        
        # Create new Item instance
        new_item = Item(
            active=True,
            item_name="",
            category_id=1,  # Default category
            description=""
        )
        
        # Get default category
        stmt = select(Category).where(Category.category_id == 1)
        category = await self.session.execute(stmt)
        category = category.scalar_one()
        
        self._data.append({
            "item": new_item,
            "category": category
        })
        
        self.new_rows.add(len(self._data) - 1)
        self.endInsertRows() 