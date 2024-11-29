import pandas as pd
from typing import Dict, List
from PySide6.QtCore import Qt, QModelIndex, Slot
from PySide6.QtGui import QColor
from model.di_data_model import DataModel
from common.d_logger import Logs
from common.datetime_utils import *
from model.item_model import ItemModel
from constants import RowFlags, EditLevel, DEFAULT_MIN_QTY
from ds_exceptions import *

logger = Logs().get_logger("main")

"""
Handling a raw dataframe from db to convert into model data(dataframe)
Also, converting model data(dataframe) back into a data class to update db
"""


class SkuModel(DataModel):
    def __init__(self, user_name: str, item_model: ItemModel):
        self.item_model = item_model
        self.init_params()
        self.selected_upper_id = None
        self.item_model.item_model_changed_signal.connect(
            self.item_model_changed)
        # setting a model is carried out in the DataModel
        super().__init__(user_name)

    def init_params(self):
        self.set_table_name('skus')

        self.col_edit_lvl = {
            'sku_id': EditLevel.NotEditable,
            'root_sku': EditLevel.Creatable,
            'item_name': EditLevel.NotEditable,
            'sub_name': EditLevel.UserModifiable,
            'active': EditLevel.AdminModifiable,
            'sku_qty': EditLevel.AdminModifiable,
            'min_qty': EditLevel.UserModifiable,
            'expiration_date': EditLevel.Creatable,
            'description': EditLevel.UserModifiable,
            'bit_code': EditLevel.AdminModifiable,
            'sku_name': EditLevel.NotEditable,
            'item_id': EditLevel.NotEditable,
            'flag': EditLevel.NotEditable
        }
        self.set_column_names(list(self.col_edit_lvl.keys()))
        self.set_column_index_edit_level(self.col_edit_lvl)

    def set_add_on_cols(self):
        """
        Needs to be implemented in the subclasses
        Adds extra columns of each name mapped to ids of supplementary data
        :return:
        """
        # set more columns for the view
        self.model_df['item_name'] = self.model_df['item_id'].map(
            lambda x: self.item_model.get_data_from_id(x, 'item_name'))
        self.model_df['sku_name'] = self.model_df['item_name'].str.cat(
            self.model_df.loc[:, 'sub_name'], na_rep="-", sep=" ").str.replace("None", "")
        self.model_df['flag'] = RowFlags.OriginalRow

    def set_upper_model_id(self, item_id: int or None):
        self.selected_upper_id = item_id
        logger.debug(f"item_id({self.selected_upper_id}) is set")

    def get_default_delegate_info(self) -> List[int]:
        """
        Returns a list of column indexes for default delegate
        :return:
        """
        default_info_list = [self.get_col_number(c) for c in
                             ['sub_name', 'description', 'bit_code']]
        return default_info_list

    def get_combobox_delegate_info(self) -> Dict[int, List]:
        """
        Returns a dictionary of column indexes and val lists of the combobox
        for combobox delegate
        :return:
        """
        combo_info_dict = {
            self.get_col_number('active'): ['Y', 'N'],
        }
        return combo_info_dict

    def get_spinbox_delegate_info(self) -> Dict[int, List]:
        """
        Returns a dictionary of column indexes and val lists of the spinbox
        for spinbox delegate
        :return:
        """
        spin_info_dict = {
            self.get_col_number('min_qty'): [0, 1000],
        }
        return spin_info_dict

    def is_active_row(self, idx: QModelIndex or int) -> bool:
        if isinstance(idx, QModelIndex):
            item_id = self.get_data_from_index(idx, 'item_id')
        else:
            item_id = self.get_data_from_id(idx, 'item_id')

        item_active = self.item_model.is_active_row(item_id)
        return item_active and super().is_active_row(idx)

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        """
        Override method from QAbstractTableModel
        QTableView accepts only QString as input for display
        Returns data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        col_name = self.get_col_name(index.column())
        data_to_display = self.model_df.iloc[index.row(), index.column()]
        if role == Qt.DisplayRole or role == Qt.EditRole or role == self.SortRole:
            int_type_columns = ['sku_id', 'root_sku', 'item_id', 'sku_qty', 'min_qty']
            if col_name in int_type_columns:
                # if column data is int, return int type
                return int(data_to_display)

            elif col_name == 'expiration_date':
                # data type is datetime.date
                return pydate_to_qdate(data_to_display)

            elif col_name == 'active':
                if data_to_display:
                    return 'Y'
                else:
                    return 'N'

            else:
                # otherwise, string type
                return str(data_to_display)

        elif role == Qt.TextAlignmentRole:
            left_aligned = ['description']
            if col_name in left_aligned:
                return Qt.AlignLeft
            else:
                return Qt.AlignCenter

        else:
            return super().data(index, role)

    def setData(self,
                index: QModelIndex,
                value: object,
                role=Qt.EditRole):
        """
        Override method from QAbstractTableModel
        :param index:
        :param value:
        :param role:
        :return:
        """
        if not index.isValid() or role != Qt.EditRole:
            return False

        logger.debug(f"index({index}) value({value})")

        col_name = self.get_col_name(index.column())
        if col_name == 'active':
            # taking care of converting str type input to bool type
            if value == 'Y':
                value = True
            else:
                value = False

        elif col_name == 'sub_name':
            item_name_col = self.get_col_number('item_name')
            sku_name_col = self.get_col_number('sku_name')
            self.model_df.iloc[index.row(), sku_name_col] = ' '.join(
                [self.model_df.iloc[index.row(), item_name_col], value])

        elif col_name == 'expiration_date':
            # data type is datetime.date
            if isinstance(value, QDate):
                value = qdate_to_pydate(value)

        elif col_name == 'root_sku':
            root_row = self.model_df.loc[self.model_df['sku_id'] == value, :]
            if root_row.empty:
                return None

            root_row_s = root_row.iloc[0].squeeze()
            item_id = index.siblingAtColumn(self.get_col_number("item_id")).data()
            if root_row_s.item_id != item_id:
                return None

        return super().setData(index, value, role)

    def is_sku_qty_correct(self, sku_id: int, sku_qty: int) -> bool:
        """
        If it is a root sku, check if it is correct
        :param root_sku:
        :return:
        """
        sku_grp = self.model_df.loc[self.model_df['root_sku'] == sku_id, 'sku_qty']
        if sku_grp.empty:
            # it does not have any sub skus, then qty is regarded correct
            return True

        sum_qty = sku_grp.sum().item()
        if sku_qty != sum_qty:
            return False
        else:
            return True

    def is_colored_cell(self, index: QModelIndex) -> bool:
        if self.get_col_name(index.column()) == "sku_qty":
            return True
        else:
            return super().is_colored_cell(index)

    def cell_color(self, index: QModelIndex) -> QColor:
        if self.get_col_name(index.column()) == "sku_qty":
            row_s = self.model_df.iloc[index.row(), :]
            if row_s.root_sku == 0 and not self.is_sku_qty_correct(row_s.sku_id, row_s.sku_qty):
                return QColor(255, 180, 150, 50)
            elif row_s.sku_qty < row_s.min_qty:
                return QColor(Qt.red)
            else:
                return super().cell_color(index)
        else:
            return super().cell_color(index)

    def make_a_new_row_df(self, next_new_id, **kwargs) -> pd.DataFrame:
        """
        Needs to be implemented in subclasses
        :param next_new_id:
        :return: new dataframe if succeeds, otherwise raise an exception
        """
        if self.selected_upper_id is None:
            error = "item_id is empty"
            raise NonExistentItemIdError(error)
        elif not self.item_model.get_data_from_id(self.selected_upper_id, 'active'):
            error = f"item_id({self.selected_upper_id}) is not active"
            raise InactiveItemIdError(error)

        default_item_id = self.selected_upper_id
        item_name = self.item_model.get_data_from_id(default_item_id, 'item_name')
        logger.debug(f"item_id({default_item_id}) item_name({item_name}) being created")
        exp_date = date(9999, 1, 1)

        new_model_df = pd.DataFrame([{
            'sku_id': next_new_id,
            'root_sku': 0,
            'item_name': item_name,
            'sub_name': "",
            'active': True,
            'sku_qty': 0,
            'min_qty': DEFAULT_MIN_QTY,
            'expiration_date': exp_date,
            'description': "",
            'bit_code': "",
            'sku_name': item_name,
            'item_id': default_item_id,
            'flag': RowFlags.NewRow
        }])
        return new_model_df

    def update_sku_qty_after_transaction(self, sku_id: int, qty: int):
        logger.debug(f"qty({qty})")
        qty_index = self.index(self.model_df[self.model_df["sku_id"] == sku_id].index[0],
                               self.get_col_number("sku_qty"),
                               QModelIndex())
        self.set_chg_flag(qty_index)
        self.setData(qty_index, qty)
        self.clear_editable_rows()

    def get_bit_codes(self) -> List:
        code_set = set(self.model_df.bit_code.to_list())
        code_set.discard('')
        return list(code_set)

    def get_bitcode_df(self) -> pd.DataFrame:
        bitcode_df = self.model_df.loc[:, ["sku_id", "bit_code"]]
        return bitcode_df[bitcode_df["bit_code"].astype(bool)]

    @Slot(object)
    def item_model_changed(self, item_ids: List):
        """
        THIS SLOT IS NOT USED FOR THE TIME BEING
        It is called when Item model is changed as follows:
            - active states
        :param item_ids:
        :return:
        """
        active_df = self.item_model.model_df.loc[
                        self.item_model.model_df.item_id in item_ids,
                        ["item_id", "active"]
                    ]
        # change the active state of skus according to the active state
        # of the item
        self.model_df.set_index('item_id', inplace=True)
        self.model_df.update(active_df.set_index('item_id'))
        self.model_df.reset_index()