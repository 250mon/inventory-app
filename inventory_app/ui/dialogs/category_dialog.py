from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QMessageBox
)
from model.models import Category

class CategoryDialog(QDialog):
    """Dialog for adding/editing categories"""
    
    def __init__(self, parent=None, category: Category = None):
        super().__init__(parent)
        self.category = category
        self._setup_ui()
        if category:
            self._load_category()
            
    def _setup_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Category Details")
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Create input fields
        self.name_edit = QLineEdit()
        self.description_edit = QLineEdit()
        
        # Add fields to form
        form_layout.addRow("Name:", self.name_edit)
        form_layout.addRow("Description:", self.description_edit)
        
        # Create buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Add layouts to main layout
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        
    def _load_category(self):
        """Load category data into fields"""
        self.name_edit.setText(self.category.category_name)
        self.description_edit.setText(self.category.description or '')
        
    def get_data(self) -> dict:
        """Get the dialog data as a dictionary"""
        return {
            'category_name': self.name_edit.text().strip(),
            'description': self.description_edit.text().strip()
        }
        
    def accept(self):
        """Validate and accept the dialog"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Category name is required")
            return
            
        super().accept() 