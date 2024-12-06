from PySide6.QtCore import Slot
from PySide6.QtWidgets import QPushButton
from ui.base_table_widget import TableWidget

class FilterableTableWidget(TableWidget):
    """Base class for tables that can be filtered by parent ID"""
    
    def __init__(self, widget_name: str, parent=None):
        super().__init__(widget_name, parent)
        self.selected_upper_id = None
        
    def _setup_filter_ui(self):
        """Setup filter controls"""
        self.search_all_btn = QPushButton('전체조회')
        self.search_all_btn.clicked.connect(self.filter_for_search_all)
        
    def set_upper_id(self, upper_id: int):
        """Set parent ID for filtering"""
        if self.model.is_model_editing():
            return
            
        self.selected_upper_id = upper_id
        self.model.set_upper_model_id(upper_id)
        self._apply_filter()
        
    def _apply_filter(self):
        """Apply filter based on upper_id"""
        if self.selected_upper_id:
            self.proxy_model.setFilterRegularExpression(f"^{self.selected_upper_id}$")
        else:
            self.proxy_model.setFilterRegularExpression("^\\d*$")
            
    @Slot()
    def filter_for_search_all(self):
        """Clear filter"""
        self.set_upper_id(None) 