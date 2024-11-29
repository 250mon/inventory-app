from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtCore import QModelIndex
from model.pandas_model import PandasModel


class DefaultDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.p_model = None

    def set_model(self, model: PandasModel):
        self.p_model = model

    def initStyleOption(self,
                        option: QStyleOptionViewItem,
                        index: QModelIndex) -> None:
        super().initStyleOption(option, index)
