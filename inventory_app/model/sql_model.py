from typing import List
from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel
from PySide6.QtGui import QColor
from config import Config

class SQLTableModel(QAbstractTableModel):
    """Base model class to interface Qt views with SQLAlchemy data"""
    
    SortRole = Qt.UserRole + 1
    
    def __init__(self):
        super().__init__()
        self._data = []  # List of SQLAlchemy model objects
        self._headers = []  # Column names
        self._column_map = {}  # Maps column names to indices
        self.editable = False
        self.edit_level = Config.EditLevel.UserModifiable
        self.editable_rows_set = set()
        self._service = None  # Service class instance
        
    def set_service(self, service):
        """Set the service class instance"""
        self._service = service
        
    async def load_data(self):
        """Load data using service class - to be implemented by subclasses"""
        raise NotImplementedError
        
    def rowCount(self, parent=None) -> int:
        return len(self._data)
        
    def columnCount(self, parent=None) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def get_col_number(self, col_name: str) -> int:
        return self._column_map.get(col_name, -1)

    def get_col_name(self, col_number: int) -> str:
        return self._headers[col_number]

    def set_editable(self, editable: bool):
        self.editable = editable
        
    def is_model_editing(self) -> bool:
        return bool(self.editable_rows_set)

    def clear_editable_rows(self):
        self.editable_rows_set.clear()

    def cell_color(self, index: QModelIndex) -> QColor:
        """Return cell color based on state"""
        if not self.is_active_row(index):
            return QColor(200, 200, 200)
        return QColor(Qt.white)

    def is_active_row(self, index: QModelIndex) -> bool:
        """Check if row is active - to be implemented by subclasses"""
        return True

    def get_clean_data(self, row: object, exclude_fields: List[str] = None) -> dict:
        """Get clean dictionary of model data, excluding internal fields
        
        Args:
            row: SQLAlchemy model instance
            exclude_fields: List of field names to exclude
            
        Returns:
            Dict containing only the relevant model data
        """
        if exclude_fields is None:
            exclude_fields = []
        exclude_fields.extend(['_sa_instance_state', 'flag'])
        
        return {
            key: getattr(row, key) 
            for key in row.__dict__.keys()
            if not key.startswith('_') and key not in exclude_fields
        }