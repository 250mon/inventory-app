import os
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Slot, QModelIndex
from PySide6.QtGui import QFont
from common.d_logger import Logs, logging
from ui.di_table_widget import InventoryTableWidget
from model.sku_model import SkuModel


logger = Logs().get_logger("main")


class SkuWidget(InventoryTableWidget):
    def __init__(self, parent: QMainWindow = None):
        super().__init__(parent)
        self.parent: QMainWindow = parent

    def set_source_model(self, model: SkuModel):
        self.source_model = model
        self._apply_model()

    def _setup_proxy_model(self):
        """
        Needs to be implemented
        :return:
        """
        # Filtering is performed on item_name column
        search_col_num = self.source_model.get_col_number('item_id')
        self.proxy_model.setFilterKeyColumn(search_col_num)

        # Sorting
        # For sorting, model data needs to be read in certain deterministic order
        # we use SortRole to read in model.data() for sorting purpose
        self.proxy_model.setSortRole(self.source_model.SortRole)
        initial_sort_col_num = self.source_model.get_col_number('sku_id')
        self.proxy_model.sort(initial_sort_col_num, Qt.AscendingOrder)

    def _setup_initial_table_view(self):
        super()._setup_initial_table_view()
        self.table_view.doubleClicked.connect(self.row_double_clicked)

    def _setup_ui(self):
        """
        Needs to be implemented
        :return:
        """
        self.set_col_hidden('item_id')
        self.set_col_width("sku_id", 50)
        self.set_col_width("root_sku", 50)
        self.set_col_width("item_name", 150)
        self.set_col_width("active", 50)
        self.set_col_width("description", 250)

        title_label = QLabel('세부품목')
        font = QFont("Arial", 12, QFont.Bold)
        title_label.setFont(font)
        hbox1 = QHBoxLayout()
        hbox1.addWidget(title_label)
        hbox1.stretch(1)

        search_all_btn = QPushButton('전체조회')
        search_all_btn.clicked.connect(self.filter_for_search_all)
        add_btn = QPushButton('추가')
        add_btn.clicked.connect(lambda: self.do_actions("add_sku"))
        del_btn = QPushButton('삭제/해제')
        del_btn.clicked.connect(lambda: self.do_actions("del_sku"))
        save_btn = QPushButton('저장')
        save_btn.clicked.connect(self.save_model_to_db)

        self.edit_mode = QGroupBox("편집 모드")
        self.edit_mode.setCheckable(True)
        self.edit_mode.setChecked(False)
        edit_hbox = QHBoxLayout()
        edit_hbox.addWidget(add_btn)
        edit_hbox.addWidget(del_btn)
        edit_hbox.addWidget(save_btn)
        self.edit_mode.setLayout(edit_hbox)
        self.edit_mode.clicked.connect(self.edit_mode_clicked)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(search_all_btn)
        hbox2.addStretch(1)
        hbox2.addWidget(self.edit_mode)

        vbox = QVBoxLayout(self)
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addWidget(self.table_view)
        self.setLayout(vbox)

    @Slot(str)
    def enable_edit_mode(self, sender: str):
        if sender != "sku_widget":
            self.edit_mode.setEnabled(True)

    @Slot(str)
    def disable_edit_mode(self, sender: str):
        if sender != "sku_widget":
            self.edit_mode.setEnabled(False)

    @ Slot()
    def edit_mode_clicked(self):
        if self.edit_mode.isChecked():
            logger.debug("Now enter into edit mode")
            self.edit_mode_starts()
        elif self.source_model.is_model_editing():
            logger.debug("The model is in the middle of editing."
                         ' Should save before exit the mode')
            QMessageBox.information(self,
                                    '편집모드 중 종료',
                                    '편집모드를 종료하려면 수정부분에 대해 먼저 저장하시거나 삭제해주세요',
                                    QMessageBox.Close)
            self.edit_mode.setChecked(True)
        else:
            logger.debug("Now edit mode ends")
            self.edit_mode_ends()

    def edit_mode_starts(self):
        self.source_model.set_editable(True)
        self.parent.edit_lock_signal.emit("sku_widget")

    def edit_mode_ends(self):
        self.source_model.set_editable(False)
        self.parent.edit_unlock_signal.emit("sku_widget")

    @Slot(str)
    def do_actions(self, action: str):
        """
        Needs to be implemented
        :param action:
        :return:
        """
        logger.debug(f"{action}")
        if action == "add_sku":
            logger.debug("Adding sku ...")
            self.add_new_row()
        elif action == "del_sku":
            logger.debug("Deleting sku ...")
            if selected_indexes := self._get_selected_indexes():
                self.delete_rows(selected_indexes)

    def save_model_to_db(self):
        """
        Save the model to DB
        It calls the inventory view's async_start() which calls back the model's
        save_to_db()
        :return:
        """
        if hasattr(self.parent, "async_start"):
            self.parent.async_start("sku_save")
        self.edit_mode.setChecked(False)
        self.edit_mode_ends()

    @Slot(QModelIndex)
    def row_double_clicked(self, index: QModelIndex):
        """
        A sku being double clicked in the sku view automatically makes
        the transaction view to do filtering to show the transactions of
        the selected sku.
        :param index:
        :return:
        """
        if not self.edit_mode.isChecked() and index.isValid() and hasattr(self.parent, 'sku_selected'):
            sku_id = index.siblingAtColumn(self.source_model.get_col_number('sku_id')).data()
            self.parent.sku_selected(sku_id)
