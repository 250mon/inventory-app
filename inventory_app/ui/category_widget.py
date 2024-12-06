from PySide6.QtGui import QFont, QLabel
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLineEdit
from ui.base_table_widget import TableWidget

class CategoryWidget(TableWidget):
    def __init__(self, parent=None):
        super().__init__("category_widget", parent)
        
    def _setup_ui(self):
        """Setup category specific UI"""
        # Column configuration
        self.set_column_widths({
            "category_id": 50,
            "category_name": 150,
            "description": 250
        })
        
        # Layout
        layout = QVBoxLayout()
        
        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel('카테고리')
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Search
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('검색어')
        self.search_bar.textChanged.connect(
            self.proxy_model.setFilterFixedString)
        search_layout.addWidget(self.search_bar)
        search_layout.addStretch()
        search_layout.addWidget(self.edit_mode)
        
        layout.addLayout(title_layout)
        layout.addLayout(search_layout)
        layout.addWidget(self.table_view)
        self.setLayout(layout) 