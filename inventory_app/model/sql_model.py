from PySide6.QtCore import Qt, QModelIndex, QAbstractTableModel
from PySide6.QtGui import QColor

class SQLTableModel(QAbstractTableModel):
    """Base model class to interface Qt views with SQLAlchemy data"""
    
    def __init__(self):
        super().__init__()
        self._data = []  # List of SQLAlchemy model objects
        self._headers = []  # Column names
        self._column_map = {}  # Maps column names to indices
        
    async def load_data(self):
        """Load data - to be implemented by subclasses"""
        raise NotImplementedError
        
    def rowCount(self, parent=None) -> int:
        """Return number of rows"""
        return len(self._data)
        
    def columnCount(self, parent=None) -> int:
        """Return number of columns"""
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        """Return header data"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def get_col_number(self, col_name: str) -> int:
        """Get column number by name"""
        return self._column_map.get(col_name, -1)

    def cell_color(self, index: QModelIndex) -> QColor:
        """Return cell color based on state"""
        if not self.is_active_row(index.row()):
            return QColor(200, 200, 200)
        return QColor(Qt.white)

    def is_active_row(self, row: int) -> bool:
        """Check if row is active - to be implemented by subclasses"""
        return True