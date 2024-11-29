import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QSpinBox,
    QVBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QDataWidgetMapper, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from model.tr_model import TrModel
from common.d_logger import Logs


logger = Logs().get_logger("main")


class SingleTrWindow(QWidget):
    create_tr_signal = Signal(object)

    def __init__(self, proxy_model: QSortFilterProxyModel, parent=None):
        super().__init__()
        self.parent = parent
        self.proxy_model = proxy_model
        self.source_model: TrModel = self.proxy_model.sourceModel()
        self.init_ui()

    def init_ui(self):
        self.nameLabel = QLabel("제품명:")
        self.nameBox = QLabel(self.source_model.selected_upper_name)
        self.trTypeLabel = QLabel("거래구분:")
        self.trTypeLE = QLineEdit()
        self.trTypeLE.setEnabled(False)
        self.qtyLabel = QLabel("수량:")
        self.qtySpinBox = QSpinBox()
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.qtySpinBox.setSizePolicy(policy)
        self.qtySpinBox.setMaximum(1000)
        self.qtySpinBox.setMinimum(0)
        self.descriptionLabel = QLabel("비고:")
        self.descriptionTextEdit = QPlainTextEdit()
        self.okButton = QPushButton("&Ok")
        self.exitButton = QPushButton("&Exit")
        self.nameLabel.setBuddy(self.nameBox)
        self.trTypeLabel.setBuddy(self.trTypeLE)
        self.qtyLabel.setBuddy(self.qtySpinBox)
        self.descriptionLabel.setBuddy(self.descriptionTextEdit)
        self.addMapper()
        # wire the signals into the parent widget
        if hasattr(self.parent, "added_new_tr_by_single_tr_window"):
            self.create_tr_signal.connect(self.parent.added_new_tr_by_single_tr_window)

        vbox = QVBoxLayout()
        vbox.addWidget(self.okButton)
        vbox.addWidget(self.exitButton)

        gridbox = QGridLayout()
        gridbox.addWidget(self.nameLabel, 0, 0, 1, 1)
        gridbox.addWidget(self.nameBox, 0, 1, 1, 1)
        gridbox.addWidget(self.trTypeLabel, 1, 0, 1, 1)
        gridbox.addWidget(self.trTypeLE, 1, 1, 1, 1)
        gridbox.addWidget(self.qtyLabel, 2, 0, 1, 1, Qt.AlignTop)
        gridbox.addWidget(self.qtySpinBox, 2, 1, 1, 1, Qt.AlignTop)
        gridbox.addWidget(self.descriptionLabel, 4, 0, 1, 1, Qt.AlignTop)
        gridbox.addWidget(self.descriptionTextEdit, 4, 1, 1, 1)

        gridbox.addLayout(vbox, 2, 2, 1, 1)

        self.setLayout(gridbox)
        self.setWindowTitle("거래 입력")
        self.show()

    def addMapper(self):
        self.mapper = QDataWidgetMapper(self)
        self.mapper.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.mapper.setModel(self.proxy_model)
        self.mapper.addMapping(self.trTypeLE, self.source_model.get_col_number('tr_type'))
        self.mapper.addMapping(self.qtySpinBox, self.source_model.get_col_number('tr_qty'))
        self.mapper.addMapping(self.descriptionTextEdit,
                               self.source_model.get_col_number('description'))

        self.okButton.clicked.connect(self.ok_clicked)
        self.exitButton.clicked.connect(self.exit_clicked)

        self.mapper.toLast()

    def ok_clicked(self):
        logger.debug(f"Created Transaction")
        self.mapper.submit()
        index = self.proxy_model.index(self.mapper.currentIndex(), 0)
        self.create_tr_signal.emit(index)
        self.close()

    def exit_clicked(self):
        # self.create_tr_signal.emit()
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    model = TrModel()
    window = SingleTrWindow(model)
    sys.exit(app.exec())
