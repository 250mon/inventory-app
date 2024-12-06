from PyQt5.QtCore import Qt
from PyQt5.QtGui import QAbstractTableModel
from model.edit_level import EditLevel

# Replace PandasModel with SQLTableModel
class SQLTableModel(QAbstractTableModel):
    """Base model class to interface Qt views with SQLAlchemy data"""
    
    def __init__(self):
        super().__init__()
        self._data = []  # List of SQLAlchemy model objects
        self._headers = []  # Column headers
        self._column_map = {}  # Maps column names to indices
        self.editable = False
        self.edit_level = EditLevel.UserModifiable
        
    def rowCount(self, parent=None):
        return len(self._data)
        
    def columnCount(self, parent=None):
        return len(self._headers)
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        row = self._data[index.row()]
        col = self._headers[index.column()]
        
        if role == Qt.DisplayRole:
            return str(getattr(row, col))
            
        return None