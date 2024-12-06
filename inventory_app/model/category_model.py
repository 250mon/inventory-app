from PySide6.QtCore import Qt, QModelIndex, Signal
from typing import List, Dict, Optional
from model.sql_model import SQLTableModel
from services.category_service import CategoryService
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")

class CategoryModel(SQLTableModel):
    category_model_changed_signal = Signal(object)
    
    def __init__(self, category_service: CategoryService):
        super().__init__()
        self._service = category_service
        self._setup_model()
        
    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = ['category_id', 'category_name', 'description', 'flag']
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'category_id': Config.EditLevel.NotEditable,
            'category_name': Config.EditLevel.AdminModifiable,
            'description': Config.EditLevel.UserModifiable,
            'flag': Config.EditLevel.NotEditable
        }
        
    async def load_data(self):
        """Load categories from service"""
        self._data = await self._service.get_categories()
        self.layoutChanged.emit()
        
    def get_category_names(self) -> List[str]:
        """Get list of category names"""
        return [cat.category_name for cat in self._data]
        
    def get_category_by_name(self, name: str) -> Optional[object]:
        """Get category object by name"""
        return next((cat for cat in self._data if cat.category_name == name), None) 