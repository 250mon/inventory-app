from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableView, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, Slot
from model.category_model import CategoryModel
from ui.dialogs.category_dialog import CategoryDialog
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")

class CategoryWidget(QWidget):
    """Widget for managing categories"""
    
    def __init__(self, user_name: str, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.model = CategoryModel()
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Initialize the UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Create buttons
        self.add_btn = QPushButton("Add Category")
        self.edit_btn = QPushButton("Edit Category")
        self.delete_btn = QPushButton("Delete Category")
        
        # Add buttons to layout
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        
        # Create table view
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        
        # Configure table view
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.SingleSelection)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Hide technical columns
        self.table_view.hideColumn(self.model.get_col_number('category_id'))
        
        # Add widgets to main layout
        layout.addLayout(button_layout)
        layout.addWidget(self.table_view)
        
        # Set initial button states
        self._update_button_states()
        
    def _connect_signals(self):
        """Connect signals to slots"""
        self.add_btn.clicked.connect(self._handle_add)
        self.edit_btn.clicked.connect(self._handle_edit)
        self.delete_btn.clicked.connect(self._handle_delete)
        self.table_view.selectionModel().selectionChanged.connect(self._update_button_states)
        
    def _update_button_states(self):
        """Update button enabled states based on selection and permissions"""
        has_selection = bool(self.table_view.selectionModel().selectedRows())
        is_admin = self.user_name in Config.ADMIN_GROUP
        
        self.add_btn.setEnabled(True)  # Always enabled
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection and is_admin)
        
    @Slot()
    async def _handle_add(self):
        """Handle adding a new category"""
        dialog = CategoryDialog(self)
        if dialog.exec():
            try:
                category_data = dialog.get_data()
                await self.model.create_category(category_data)
                await self.refresh_data()
            except Exception as e:
                logger.error(f"Error creating category: {e}")
                QMessageBox.critical(self, "Error", f"Failed to create category: {str(e)}")
                
    @Slot()
    async def _handle_edit(self):
        """Handle editing selected category"""
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
            
        row = selected[0].row()
        category = self.model._data[row]
        
        dialog = CategoryDialog(self, category)
        if dialog.exec():
            try:
                category_data = dialog.get_data()
                await self.model.update_category(category.category_id, category_data)
                await self.refresh_data()
            except Exception as e:
                logger.error(f"Error updating category: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update category: {str(e)}")
                
    @Slot()
    async def _handle_delete(self):
        """Handle deleting selected category"""
        if self.user_name not in Config.ADMIN_GROUP:
            QMessageBox.warning(self, "Permission Denied", "Only administrators can delete categories")
            return
            
        selected = self.table_view.selectionModel().selectedRows()
        if not selected:
            return
            
        row = selected[0].row()
        category = self.model._data[row]
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete category '{category.category_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                await self.model.delete_category(category.category_id)
                await self.refresh_data()
            except Exception as e:
                logger.error(f"Error deleting category: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete category: {str(e)}")
                
    async def refresh_data(self):
        """Refresh the model data"""
        await self.model.load_data()