from PySide6.QtWidgets import QWidget, QMainWindow, QPushButton, QHBoxLayout, QGroupBox
from PySide6.QtCore import Signal

class EditModeWidget(QWidget):
    """Base widget class with edit mode functionality"""
    
    edit_started = Signal(str)  # Emits widget_name
    edit_ended = Signal(str)    # Emits widget_name
    
    def __init__(self, widget_name: str, parent: QMainWindow = None):
        super().__init__(parent)
        self.widget_name = widget_name
        self.parent = parent
        self._setup_edit_mode()
        
    def _setup_edit_mode(self):
        """Setup edit mode controls"""
        self.edit_mode = QGroupBox("편집 모드")
        self.edit_mode.setCheckable(True)
        self.edit_mode.setChecked(False)
        
        # Standard edit buttons
        self.add_btn = QPushButton('추가')
        self.delete_btn = QPushButton('삭제/해제')
        self.save_btn = QPushButton('저장')
        
        edit_hbox = QHBoxLayout()
        edit_hbox.addWidget(self.add_btn)
        edit_hbox.addWidget(self.delete_btn)
        edit_hbox.addWidget(self.save_btn)
        self.edit_mode.setLayout(edit_hbox)
        
        # Connect signals
        self.edit_mode.clicked.connect(self._on_edit_mode_clicked)
        self.add_btn.clicked.connect(self._on_add)
        self.delete_btn.clicked.connect(self._on_delete)
        self.save_btn.clicked.connect(self._on_save)
        
    def _on_edit_mode_clicked(self, checked: bool):
        """Handle edit mode toggle"""
        if checked:
            if not self.can_start_editing():
                self.edit_mode.setChecked(False)
                return
            self.edit_started.emit(self.widget_name)
        else:
            if not self.can_end_editing():
                self.edit_mode.setChecked(True)
                return
            self.edit_ended.emit(self.widget_name)
            
    def can_start_editing(self) -> bool:
        """Check if editing can start"""
        return True
        
    def can_end_editing(self) -> bool:
        """Check if editing can end"""
        return not self.model.is_model_editing() 