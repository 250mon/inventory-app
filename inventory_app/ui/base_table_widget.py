from PySide6.QtWidgets import QTableView, QMainWindow
from PySide6.QtCore import Qt
from ui.base_edit_widget import EditModeWidget

class TableWidget(EditModeWidget):
    """Base widget class for tables with filtering and sorting"""
    
    def __init__(self, widget_name: str, parent: QMainWindow = None):
        super().__init__(widget_name, parent)
        self._setup_table()
        
    def _setup_table(self):
        """Setup table view with common configuration"""
        self.table_view = QTableView(self)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        
        # Common styling
        self.setStyleSheet(
            "QTableView::item:selected"
            "{"
            "background-color : #d9fffb;"
            "selection-color : #000000;"
            "}"
        )
        
    def set_column_widths(self, width_map: dict):
        """Set column widths from a mapping"""
        for col_name, width in width_map.items():
            col_idx = self.model.get_col_number(col_name)
            self.table_view.setColumnWidth(col_idx, width)
            
    def hide_columns(self, column_names: list):
        """Hide specified columns"""
        for col_name in column_names:
            col_idx = self.model.get_col_number(col_name)
            self.table_view.setColumnHidden(col_idx, True) 