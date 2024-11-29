from typing import List
from abc import abstractmethod
from PySide6.QtWidgets import QMainWindow, QWidget, QMessageBox, QTableView
from PySide6.QtCore import Slot, QSortFilterProxyModel, QModelIndex
from model.di_data_model import DataModel
from ui.di_default_delegate import DefaultDelegate
from ui.combobox_delegate import ComboBoxDelegate
from ui.spinbox_delegate import SpinBoxDelegate
from common.d_logger import Logs

logger = Logs().get_logger("main")


class InventoryTableWidget(QWidget):
    def __init__(self, parent: QMainWindow = None):
        super().__init__(parent)
        self.parent: QMainWindow = parent
        self.source_model = None

        self.parent.edit_lock_signal.connect(self.disable_edit_mode)
        self.parent.edit_unlock_signal.connect(self.enable_edit_mode)

    def set_source_model(self, model: DataModel):
        """
        Common
        :param model:
        :return:
        """
        self.source_model: DataModel = model
        self._apply_model()

    def _apply_model(self):
        """
        Common
        :return:
        """
        # QSortFilterProxyModel enables filtering columns and sorting rows
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.source_model)
        self._setup_proxy_model()

        self._setup_initial_table_view()
        self.table_view.setModel(self.proxy_model)
        self._setup_delegate_for_columns()

        self._setup_ui()

    @abstractmethod
    def _setup_proxy_model(self):
        """
        Needs to be implemented
        :return:
        """

    def _setup_initial_table_view(self):
        """
        Carried out before the model is set to the table view
        :return:
        """
        # table view
        self.table_view = QTableView(self)
        # self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.resizeColumnsToContents()
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.setStyleSheet(
            "QTableView::item:selected"
            "{"
            "background-color : #d9fffb;"
            "selection-color : #000000;"
            "}"
        )

    def _setup_delegate_for_columns(self):
        """
        Sets up appropriate delegates for columns
        :return:
        """
        for col_idx in self.source_model.get_default_delegate_info():
            default_delegate = DefaultDelegate(self)
            default_delegate.set_model(self.source_model)
            self.table_view.setItemDelegateForColumn(col_idx, default_delegate)

        for col_idx, val_list in self.source_model.get_combobox_delegate_info().items():
            combo_delegate = ComboBoxDelegate(val_list, self)
            combo_delegate.set_model(self.source_model)
            self.table_view.setItemDelegateForColumn(col_idx, combo_delegate)

        for col_idx, val_list in self.source_model.get_spinbox_delegate_info().items():
            spin_delegate = SpinBoxDelegate(*val_list, self)
            spin_delegate.set_model(self.source_model)
            self.table_view.setItemDelegateForColumn(col_idx, spin_delegate)

    @abstractmethod
    def _setup_ui(self):
        """
        Needs to be implemented
        :return:
        """

    @Slot()
    def enable_edit_mode(self):
        pass

    @Slot()
    def disable_edit_mode(self):
        pass


    def _get_selected_indexes(self):
        """
        Common
        :return:
        """
        # the indexes of proxy model
        selected_indexes = self.table_view.selectedIndexes()
        is_valid_indexes = []
        rows = []
        for idx in selected_indexes:
            is_valid_indexes.append(idx.isValid())
            rows.append(idx.row())

        if len(selected_indexes) > 0 and False not in is_valid_indexes:
            logger.debug(f"Indexes selected: {rows}")
            return selected_indexes
        else:
            logger.debug(f"Indexes not selected or invalid: {selected_indexes}")
            return None

    @Slot(str)
    def do_actions(self, action: str):
        """
        Needs to be implemented
        :param action:
        :return:
        """

    def add_new_row(self, **kwargs):
        """
        Common
        This is called from a Button
        :return:
        """
        try:
            self.source_model.append_new_row(**kwargs)
        except Exception as e:
            QMessageBox.information(self,
                                    "Failed New Sku",
                                    # "세부품목을 먼저 선택하세요.",
                                    str(e),
                                    QMessageBox.Close)

    def change_rows(self, indexes: List[QModelIndex]):
        """
        Common
        This is called from a Button
        Just tagging as 'changed' in flag column and allowing the user
        to modify the items
        :param indexes:
        :return:
        """
        for idx in indexes:
            if self.source_model.is_flag_column(idx):
                src_idx = self.proxy_model.mapToSource(idx)
                self.source_model.set_chg_flag(src_idx)
                logger.debug(f"rows {src_idx.row()} being changed")

    def delete_rows(self, indexes: List[QModelIndex]):
        """
        Common
        This is called from a Button
        Just tagging as 'deleted' in flag column instead of dropping
        Actual dropping is done during saving into DB
        :param indexes:
        :return:
        """
        del_indexes = []
        for idx in indexes:
            # do it only once for multiple indexes belonging to the same row
            if self.source_model.is_flag_column(idx):
                src_idx = self.proxy_model.mapToSource(idx)
                del_indexes.append(src_idx)

        if len(del_indexes) > 0:
            self.source_model.set_del_flag(del_indexes)
            rows = [idx.row() for idx in del_indexes]
            logger.debug(f"rows {rows} deleted")

    async def save_to_db(self):
        """
        Common
        :return:
        """
        return await self.source_model.save_to_db()

    def filter_for_selected_upper_id(self, id: int):
        """
        A double click event that triggers the upper level widget's
        row_selected method eventually calls this method
        :param item_id:
        :return:
        """
        # if there is remaining unsaved new rows, drop them
        self.source_model.del_new_rows()
        # let the model learn the upper model index for a new row creation
        self.source_model.set_upper_model_id(id)

        # filtering in the sku view
        self.proxy_model.setFilterRegularExpression(
            f"^{self.source_model.selected_upper_id}$")

    def filter_for_search_all(self):
        """
        Connected to search all button
        :return:
        """
        # if there is remaining unsaved new rows, drop them
        self.source_model.del_new_rows()
        self.source_model.set_upper_model_id(None)
        self.proxy_model.setFilterRegularExpression("^\\d*$")

    def set_col_width(self, col_name:str, width: int):
        self.table_view.setColumnWidth(self.source_model.get_col_number(col_name), width)

    def set_col_hidden(self, left_most_hidden: str):
        left_most_col_num = self.source_model.get_col_number(left_most_hidden)
        last_col_num = len(self.source_model.column_names)
        for c in range(left_most_col_num, last_col_num):
            self.table_view.setColumnWidth(c, 1)
            # The following methods don't allow the hidden col
            # to be accessible
            # self.table_view.horizontalHeader().hideSection(c)
            # self.table_view.setColumnHidden(c, True)
            # filterAcceptsColumn..
