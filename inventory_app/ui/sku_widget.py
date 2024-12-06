import os
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Slot, QModelIndex
from PySide6.QtGui import QFont
from common.d_logger import Logs, logging
from ui.filterable_table_widget import FilterableTableWidget
from model.sku_model import SkuModel
from qasync import asyncSlot


logger = Logs().get_logger("main")


class SkuWidget(FilterableTableWidget):
    def __init__(self, parent=None):
        super().__init__("sku_widget", parent)

    def _setup_ui(self):
        """Setup SKU specific UI"""
        # Column configuration
        self.set_column_widths({
            "sku_id": 50,
            "root_sku": 50,
            "item_name": 150,
            "active": 50,
            "description": 250
        })
        self.hide_columns(['item_id'])
        
        # Layout
        layout = QVBoxLayout()
        
        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel('세부품목')
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        self._setup_filter_ui()
        filter_layout.addWidget(self.search_all_btn)
        filter_layout.addStretch()
        filter_layout.addWidget(self.edit_mode)
        
        layout.addLayout(title_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(self.table_view)
        self.setLayout(layout)
        
    def _on_row_double_clicked(self, index):
        """Handle row double click"""
        if not self.edit_mode.isChecked() and index.isValid():
            sku_id = index.siblingAtColumn(
                self.model.get_col_number('sku_id')).data()
            self.parent.sku_selected(sku_id)
