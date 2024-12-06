from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QDateEdit
)
from PySide6.QtCore import Qt, Slot, QDate
from common.d_logger import Logs
from ui.filterable_table_widget import FilterableTableWidget

logger = Logs().get_logger("main")


class TrWidget(FilterableTableWidget):
    def __init__(self, parent=None):
        super().__init__("tr_widget", parent)
        self._setup_date_range()
        
    def _setup_date_range(self):
        """Setup date range controls"""
        self.beg_date = QDateEdit()
        self.end_date = QDateEdit()
        self.beg_date.setDate(QDate.currentDate().addMonths(-6))
        self.end_date.setDate(QDate.currentDate())
        
        self.date_search_btn = QPushButton('조회')
        self.date_search_btn.clicked.connect(self._on_date_search)
        
    def _setup_ui(self):
        """Setup transaction specific UI"""
        # Column configuration
        self.set_column_widths({
            "tr_id": 50,
            "tr_type": 80,
            "tr_qty": 60,
            "tr_timestamp": 200,
            "description": 600
        })
        self.hide_columns(['tr_type_id', 'user_id'])
        
        # Layout
        layout = QVBoxLayout()
        
        # Date range
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel('거래내역'))
        date_layout.addWidget(self.beg_date)
        date_layout.addWidget(self.end_date)
        date_layout.addWidget(self.date_search_btn)
        date_layout.addStretch()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        self._setup_filter_ui()
        filter_layout.addWidget(self.search_all_btn)
        filter_layout.addStretch()
        filter_layout.addWidget(self.edit_mode)
        
        layout.addLayout(date_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.table_view)
        self.setLayout(layout)
        
    @Slot()
    def _on_date_search(self):
        """Handle date range search"""
        self.model.set_date_range(
            self.beg_date.date().toPython(),
            self.end_date.date().toPython()
        )
        self._apply_filter()
