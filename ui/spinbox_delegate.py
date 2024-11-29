from PySide6.QtWidgets import (
    QWidget, QStyleOptionViewItem, QSpinBox
)
from PySide6.QtCore import QModelIndex, Qt, QAbstractItemModel
from ui.di_default_delegate import DefaultDelegate


class SpinBoxDelegate(DefaultDelegate):
    def __init__(self, min=0, max=10, parent=None):
        super().__init__(parent)
        self.min = min
        self.max = max

    def createEditor(self,
                     parent: QWidget,
                     option: QStyleOptionViewItem,
                     index: QModelIndex) -> QWidget:
        editor = QSpinBox(parent)
        editor.setMinimum(self.min)
        editor.setMaximum(self.max)
        return editor

    def setEditorData(self,
                      editor: QSpinBox,
                      index: QModelIndex) -> None:
        data_val = index.data()
        editor.setValue(data_val)

    def setModelData(self,
                     editor: QSpinBox,
                     model: QAbstractItemModel,
                     index: QModelIndex) -> None:
        editor_val = editor.value()
        model.setData(index, editor_val, Qt.EditRole)

    def updateEditorGeometry(self,
                             editor: QSpinBox,
                             option: QStyleOptionViewItem,
                             index: QModelIndex) -> None:
        editor.setGeometry(option.rect)

