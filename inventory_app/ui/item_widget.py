from typing import List
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt, Slot, QModelIndex, QSortFilterProxyModel
from PySide6.QtGui import QFont
from common.d_logger import Logs
from model.item_model import ItemModel
from qasync import asyncSlot
from ui.base_table_widget import TableWidget

logger = Logs().get_logger("main")


class ItemWidget(TableWidget):
    def __init__(self, parent: QMainWindow = None):
        super().__init__("item_widget", parent)
        self.delegate_mode = True  # For handling input methods
        
    def set_model(self, model: ItemModel):
        """Set model and setup proxy"""
        self.model = model
        
        # Setup proxy model for filtering and sorting
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(-1)  # Search all columns
        self.proxy_model.setSortRole(self.model.SortRole)
        
        # Set model to view
        self.table_view.setModel(self.proxy_model)
        self.table_view.sortByColumn(
            self.model.get_col_number('item_id'), 
            Qt.AscendingOrder
        )
        
        # Connect double click handler
        self.table_view.doubleClicked.connect(self._on_row_double_clicked)
        
    def _setup_ui(self):
        """Setup item specific UI"""
        # Column configuration
        self.set_column_widths({
            "item_id": 50,
            "active": 50,
            "item_name": 150,
            "description": 150
        })
        self.hide_columns(['category_id'])
        
        # Layout
        layout = QVBoxLayout()
        
        # Title
        title_layout = QHBoxLayout()
        title_label = QLabel('품목')
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        refresh_btn = QPushButton('전체새로고침')
        refresh_btn.clicked.connect(self._on_refresh)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(refresh_btn)
        
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

    def _on_add(self):
        """Handle add button click"""
        try:
            self.model.append_new_row()
            if not self.delegate_mode:
                # Use input window if not using delegate mode
                new_item_index = self.model.index(self.model.rowCount()-1, 0)
                self._show_item_window(new_item_index)
        except Exception as e:
            QMessageBox.warning(self, "Add Failed", str(e))

    def _on_delete(self):
        """Handle delete button click"""
        selected = self.table_view.selectedIndexes()
        if not selected:
            return
            
        # Get unique rows
        rows = set(idx.row() for idx in selected)
        source_indexes = [
            self.proxy_model.mapToSource(
                self.proxy_model.index(row, 0)
            ) for row in rows
        ]
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 
            'Confirm Delete',
            f'Delete {len(rows)} selected items?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for idx in source_indexes:
                self.model.set_del_flag([idx])

    @asyncSlot()
    async def _on_save(self):
        """Handle save button click"""
        try:
            await self.model.save_changes()
            self.edit_mode.setChecked(False)
            self.edit_ended.emit(self.widget_name)
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))

    @Slot()
    def _on_refresh(self):
        """Handle refresh button click"""
        self.parent.update_all_signal.emit()

    def _on_row_double_clicked(self, index: QModelIndex):
        """Handle row double click"""
        if not self.edit_mode.isChecked() and index.isValid():
            item_id = index.siblingAtColumn(
                self.model.get_col_number('item_id')).data()
            self.parent.item_selected(item_id)

    def can_start_editing(self) -> bool:
        """Check if editing can start"""
        if self.model.is_model_editing():
            QMessageBox.warning(
                self,
                "Edit Mode",
                "Cannot start editing while changes are pending"
            )
            return False
        return True

    def can_end_editing(self) -> bool:
        """Check if editing can end"""
        if self.model.is_model_editing():
            QMessageBox.warning(
                self,
                "Edit Mode",
                "Save or discard changes before ending edit mode"
            )
            return False
        return True
