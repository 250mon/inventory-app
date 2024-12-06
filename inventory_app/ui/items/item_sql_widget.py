from PySide6.QtWidgets import (
    QWidget, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout,
    QLabel, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QFont
from model.items.item_sql_model import ItemSQLModel
from ui.base_table_widget import BaseTableWidget
from common.d_logger import Logs

logger = Logs().get_logger("main")

class ItemSQLWidget(BaseTableWidget):
    """Widget for displaying and editing items"""
    
    edit_started = Signal(str)  # Emits widget name when edit mode starts
    edit_ended = Signal(str)    # Emits widget name when edit mode ends
    
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self.setup_ui()
        
    def setup_ui(self):
        """Setup widget UI elements"""
        # Title
        title_label = QLabel('Items')
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        
        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText('Search...')
        self.search_bar.textChanged.connect(self.filter_items)
        
        # Buttons
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh_data)
        
        add_btn = QPushButton('Add')
        add_btn.clicked.connect(self.add_item)
        
        delete_btn = QPushButton('Delete')
        delete_btn.clicked.connect(self.delete_items)
        
        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.save_changes)
        
        # Edit mode group
        self.edit_group = QGroupBox("Edit Mode")
        self.edit_group.setCheckable(True)
        self.edit_group.setChecked(False)
        
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(add_btn)
        edit_layout.addWidget(delete_btn)
        edit_layout.addWidget(save_btn)
        self.edit_group.setLayout(edit_layout)
        
        # Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(refresh_btn)
        
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_bar)
        search_layout.addStretch()
        search_layout.addWidget(self.edit_group)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.table_view)
        
        self.setLayout(main_layout)
        
    def set_model(self, model: ItemSQLModel):
        """Set the model and configure the view"""
        self.model = model
        self.table_view.setModel(self.model)
        
        # Hide technical columns
        self.table_view.hideColumn(self.model.get_col_number('category_id'))
        
        # Set column widths
        self.table_view.setColumnWidth(self.model.get_col_number('item_id'), 50)
        self.table_view.setColumnWidth(self.model.get_col_number('active'), 50)
        self.table_view.setColumnWidth(self.model.get_col_number('item_name'), 150)
        self.table_view.setColumnWidth(self.model.get_col_number('description'), 200)
        
    @Slot()
    async def refresh_data(self):
        """Refresh data from database"""
        await self.model.load_data()
        
    @Slot()
    def add_item(self):
        """Add new item row"""
        if not self.edit_group.isChecked():
            return
        self.model.add_new_row()
        
    @Slot()
    def delete_items(self):
        """Delete selected items"""
        if not self.edit_group.isChecked():
            return
            
        indexes = self.table_view.selectedIndexes()
        if not indexes:
            return
            
        reply = QMessageBox.question(
            self, 'Delete Items',
            'Are you sure you want to delete the selected items?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            rows = set(index.row() for index in indexes)
            for row in rows:
                self.model.delete_row(self.model.index(row, 0))
                
    @Slot()
    async def save_changes(self):
        """Save changes to database"""
        if not self.edit_group.isChecked():
            return
            
        success = await self.model.save_changes()
        if success:
            self.edit_group.setChecked(False)
            QMessageBox.information(self, 'Success', 'Changes saved successfully')
        else:
            QMessageBox.warning(self, 'Error', 'Failed to save changes')
            
    @Slot(str)
    def filter_items(self, text: str):
        """Filter items by search text"""
        # Implementation depends on your filtering needs
        pass 