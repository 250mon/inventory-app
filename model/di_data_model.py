import pandas as pd
import asyncpg.exceptions
from typing import Dict, List
from abc import abstractmethod
from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtGui import QColor, QBrush
from model.pandas_model import PandasModel
from db.di_lab import Lab
from common.d_logger import Logs
from constants import EditLevel, RowFlags, UserPrivilege, ADMIN_GROUP

logger = Logs().get_logger("main")

"""
Handling a raw dataframe from db to convert into model data(dataframe)
Also, converting model data(dataframe) back into a data class to update db
"""
class DataModel(PandasModel):
    def __init__(self, user_name):
        super().__init__()

        # for access control
        self.user_name = user_name
        if self.user_name in ADMIN_GROUP:
            self.usr_edit_lvl = EditLevel.AdminModifiable
        else:
            self.usr_edit_lvl = EditLevel.UserModifiable
        self.set_edit_level(self.usr_edit_lvl)

        # a list of columns which are used to make a df updating db
        self.db_column_names = None

        # set model_df
        self._set_model_df()

        # by selecting an id of the upper layer,
        # the lower layer view is updated
        self.selected_upper_id = None

    def get_user_privilege(self):
        if self.user_name in ADMIN_GROUP:
            return UserPrivilege.Admin
        else:
            return UserPrivilege.User

    def set_table_name(self, table_name: str):
        self.table_name = table_name

    def set_column_names(self, column_names: List[str]):
        self.column_names = column_names

    def set_column_index_edit_level(self, col_edit_lvl: Dict[str, EditLevel]):
        """
        Converts column name to column index in the Dict
        And register it to the Pandas model
        :param col_edit_lvl:
        :return:
        """
        col_idx_edit_lvl = {}
        for col_name, lvl in col_edit_lvl.items():
            col_idx = self.column_names.index(col_name)
            col_idx_edit_lvl[col_idx] = lvl
        super().set_column_index_edit_level(col_idx_edit_lvl)

    def get_col_number(self, col_name: str) -> int:
        return self.model_df.columns.get_loc(col_name)

    def get_col_name(self, col_num: int) -> str:
        return self.model_df.columns[col_num]

    def is_flag_column(self, index: QModelIndex) -> bool:
        flag_col = self.get_col_number('flag')
        return index.column() == flag_col

    def get_data_from_index(self, index: QModelIndex, col: str) -> object:
        # if not index.isValid():
        #     return None
        # elif col not in self.column_names:
        #     return None
        return self.model_df.iloc[index.row(), self.get_col_number(col)]

    def get_data_from_id(self, id: int, col: str) -> object:
        # if id not in self.model_df.iloc[:, 0].values:
        #     return None
        # elif col not in self.column_names:
        #     return None
        return self.model_df.loc[self.model_df.iloc[:, 0] == id, col].item()

    def set_flag(self, index: QModelIndex, flag: int):
        """
        Set the flag to the row where the index belongs to
        :param index:
        :param flag:
        :return:
        """
        self.model_df.iloc[index.row(), self.get_col_number('flag')] = flag

    def set_upper_model_id(self, index: QModelIndex or None):
        """
        Needs to be implemented if necessary
        upper model index is used for filtering
        :param index:
        :return:
        """
        pass

    @abstractmethod
    def set_add_on_cols(self) -> None:
        """
        Needs to be implemented in the subclasses
        Adds extra columns of each name mapped to ids of auxiliary data
        :return:
        """

    def _set_model_df(self):
        """
        Makes DataFrame out of data received from DB
        :return:
        """
        logger.debug(f"setting the df of Lab to {self.table_name}_model_f")
        self.model_df = Lab().table_df[self.table_name]

        # we store the columns list here for later use of db update
        self.db_column_names = Lab().table_column_names[self.table_name]

        # reindexing in the order of table view
        self.model_df = self.model_df.reindex(self.column_names, axis=1)

        # fill name columns against ids of each auxiliary data
        self.set_add_on_cols()

    def update_model_df_from_db(self):
        """
        Update the model_df and the view
        :return:
        """
        logger.debug(f"Update the model_df and the view")
        self._set_model_df()
        self.layoutAboutToBeChanged.emit()
        self.layoutChanged.emit()

    async def update(self, **kwargs):
        """
        Update the model whenever relevant DB data changes
        Called by inventory_view
        If there needs any model specific update, it's implemented in
        the subclasses
        :return:
        """
        logger.debug("Downloading data from DB")
        await Lab().update_lab_df_from_db(self.table_name, **kwargs)
        logger.debug("Updating the model and view")
        self.update_model_df_from_db()

    def get_default_delegate_info(self) -> List[int]:
        """
        Returns a list of column indexes for default delegate
        :return:
        """
        return []

    def get_combobox_delegate_info(self) -> Dict[int, List]:
        """
        Returns a dictionary of column indexes and val lists of the combobox
        for combobox delegate
        :return:
        """
        return {}

    def get_spinbox_delegate_info(self) -> Dict[int, List]:
        """
        Returns a dictionary of column indexes and val lists of the spinbox
        for spinbox delegate
        :return:
        """
        return {}

    def is_active_row(self, idx: QModelIndex or int) -> bool:
        """
        Default implementation
        :param idx: QModelIndex or id
        :return:
        """
        if isinstance(idx, QModelIndex):
            # index is given as an arg
            active_val = self.get_data_from_index(idx, 'active')
        else:
            # id is given as an arg
            active_val = self.get_data_from_id(idx, 'active')

        return active_val

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        if role == Qt.BackgroundRole:
            flag = self.get_data_from_index(index, 'flag')
            if flag & RowFlags.DeletedRow > 0:
                return QBrush(Qt.darkGray)
            elif not self.is_active_row(index):
                return QBrush(Qt.lightGray)
            elif self.is_colored_cell(index):
                # if the cell needs colored background depending on the
                # contents like sku_qty
                return QBrush(self.cell_color(index))
            elif flag & RowFlags.NewRow > 0:
                if self.col_idx_edit_lvl[index.column()] <= EditLevel.Creatable:
                    return QBrush(QColor(255, 255, 0))
                else:
                    return QBrush(QColor(255, 255, 0, 25))
            elif flag & RowFlags.ChangedRow > 0:
                if self.col_idx_edit_lvl[index.column()] <= self.edit_level:
                    return QBrush(QColor(0, 255, 0))
                else:
                    return QBrush(QColor(0, 255, 0, 25))
            else:
                if self.col_idx_edit_lvl[index.column()] <= self.edit_level:
                    return QBrush(QColor(100, 255, 255, 25))
                else:
                    return QBrush(Qt.transparent)
        else:
            return None

    def setData(self,
                index: QModelIndex,
                value: object,
                role=Qt.EditRole):

        flag = self.get_data_from_index(index, 'flag')
        # Unless it is a deleted row, proceed to set the data
        if flag & RowFlags.DeletedRow > 0:
            logger.debug("Cannot change data in the deleted row")
            return

        result = super().setData(index, value, role)

        # Unless it is a new row, set the change flag
        if flag & RowFlags.NewRow == 0:
            self.set_chg_flag(index)

        return result

    def is_colored_cell(self, index: QModelIndex) -> bool:
        """
        Use it if any special color is needed for a particular cell
        :param index:
        :return:
        """
        return False

    def cell_color(self, index: QModelIndex) -> QColor:
        """
        If it is a colored cell, return a appropriate color
        :param index:
        :return:
        """
        return QColor(Qt.white)

    def append_new_row(self, **kwargs):
        """
        Appends a new row to the end of the model
        :return: raise an exception if failed
        """
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())

        if self.model_df.empty:
            next_new_id = 1
        else:
            next_new_id = self.model_df.iloc[:, 0].max() + 1
        logger.debug(f"New model_df_row id({next_new_id})")

        try:
            new_row_df = self.make_a_new_row_df(next_new_id, **kwargs)
        except Exception as e:
            raise e

        if self.model_df.empty:
            self.model_df = new_row_df
        else:
            self.model_df = pd.concat([self.model_df, new_row_df], ignore_index=True)

        self.endInsertRows()

        # handles model flags
        self.set_new_row(self.rowCount() - 1)

    @abstractmethod
    def make_a_new_row_df(self, next_new_id, **kwargs):
        """
        Needs to be implemented in subclasses
        :param next_new_id:
        :return:
        """

    def drop_rows(self, indexes: List[QModelIndex or int]):
        """
        Drop rows from model_df
        :param indexes:
        :return:
        """
        logger.debug(f"dropping... indexes({indexes})")
        if isinstance(indexes[0], QModelIndex):
            indexes = [i.row() for i in indexes]

        self.beginRemoveRows(QModelIndex(), indexes[0], indexes[-1])
        self.model_df.drop(pd.Index(indexes), inplace=True)
        self.endRemoveRows()

        logger.debug(f"model_df dropped rows {indexes}")

    def diff_row(self, index: QModelIndex) -> bool:
        """
        Compare the df against the original data which is stored
        in the Lab
        :param index:
        :return: True if any difference or False if same
        """
        original_row_count = Lab().table_df[self.table_name].shape[0]
        if index.row() >= original_row_count:
            logger.error(f"index.row({index.row()} is out of "
                         f'range of model_df row count {original_row_count} ')
            exit(1)
        original_row = Lab().table_df[self.table_name].iloc[[index.row()], :]
        current_row = self.model_df.loc[self.model_df.index[[index.row()]],
                                         original_row.columns]
        if original_row.compare(current_row).empty:
            return False
        else:
            return True

    def set_chg_flag(self, index: QModelIndex):
        """
        Sets a 'changed' flag in the flag column of the row of index
        :param index:
        :return:
        """
        curr_flag = self.get_data_from_index(index, 'flag')
        curr_flag |= RowFlags.ChangedRow
        if self.diff_row(index):
            self.set_flag(index, curr_flag)

    def set_del_flag(self, indexes: List[QModelIndex]):
        """
        Sets a 'deleted' flag in the flag column of the row of index
        If it is a new row, just drop it
        Otherwise, toggle the flag
        :param index:
        :return:
        """
        flags = [self.get_data_from_index(index, 'flag') for index in indexes]
        is_new = [flag & RowFlags.NewRow for flag in flags]
        new_idxes = [index for index, cond in zip(indexes, is_new)
                       if cond > 0]
        other_idxes = [index for index in indexes
                       if index not in new_idxes]
        if len(new_idxes) > 0:
            # if it is a new row, just drop it
            self.drop_rows(new_idxes)
            for index in new_idxes:
                self.unset_new_row(index.row())

        # exclusive or op with deleted flag
        for index in other_idxes:
            curr_flag = self.get_data_from_index(index, 'flag')
            curr_flag ^= RowFlags.DeletedRow
            self.set_flag(index, curr_flag)

            if curr_flag & RowFlags.DeletedRow > 0:
                # if it is deleted, make it uneditable
                self.set_uneditable_row(index.row())
            else:
                self.unset_uneditable_row(index.row())

    def del_new_rows(self) -> int:
        """
        Remove new rows (unsaved) by means of set_del_flag
        :return: the number of deleted new rows
        """
        row_list = self.model_df[self.model_df.flag & RowFlags.NewRow > 0].index.to_list()
        if len(row_list) > 0:
            logger.debug(f"rows to delete: {row_list}")
            indexes = [self.index(row, 0) for row in row_list]
            self.set_del_flag(indexes)
        return len(row_list)

    def get_new_df(self) -> pd.DataFrame:
        return self.model_df.loc[self.model_df['flag'] & RowFlags.NewRow > 0, :]

    def get_deleted_df(self) -> pd.DataFrame:
        return self.model_df.loc[self.model_df['flag'] & RowFlags.DeletedRow > 0, :]

    def get_changed_df(self) -> pd.DataFrame:
        return self.model_df.loc[self.model_df['flag'] & RowFlags.ChangedRow > 0, :]

    async def save_to_db(self):
        """
        Updates DB reflecting the changes made to model_df
        :return:
        """
        def make_return_msg(total_results: Dict[str, str or None]):
            messages = {}
            # total_results are composed of 3 results: new, chg, del
            # Each result are composed of result from multiple queries
            for op_type, result in total_results.items():
                if result is None:
                    msg = '성공!!'
                elif isinstance(result, asyncpg.exceptions.ForeignKeyViolationError):
                    msg = f'항목이 현재 사용 중이므로 삭제할 수 없습니다.'
                elif isinstance(result, asyncpg.exceptions.UniqueViolationError):
                    msg = f'중복 데이터가 존재합니다. 항목 새로 만들기가 실패하였습니다.'
                else:
                    msg = str(result)

                messages[op_type] = msg

            return_msg = f'<{self.table_name} RESULTS>'
            for op_type, msg in messages.items():
                return_msg += ('\n' + op_type + ': ' + msg)
            return return_msg

        logger.debug("Saving to DB ...")

        total_results = {}

        del_df = self.get_deleted_df()
        if not del_df.empty:
            self.drop_rows(del_df.index.to_list())
            logger.debug(f"\n{del_df}")
            # DB data is to be deleted from here
            df_to_upload = del_df.loc[:, self.db_column_names]
            logger.debug(f"\n{df_to_upload}")
            results_del = await Lab().delete_df(self.table_name, df_to_upload)
            total_results['삭제'] = results_del
            logger.debug(f"result of deleting = {results_del}")

        new_df = self.get_new_df()
        if not new_df.empty:
            new_df.loc[:, [self.get_col_name(0)]] = 'DEFAULT'
            logger.debug(f"\n{new_df}")
            df_to_upload = new_df.loc[:, self.db_column_names]
            # set id default to let DB assign an id without collision
            # df_to_upload.loc[:, self.get_col_name(0)] = 'DEFAULT'
            logger.debug(f"\n{df_to_upload}")
            results_new = await Lab().insert_df(self.table_name, df_to_upload)
            total_results['추가'] = results_new
            logger.debug(f"result of inserting new rows = {results_new}")

        chg_df = self.get_changed_df()
        if not chg_df.empty:
            logger.debug(f"\n{chg_df}")
            df_to_upload = chg_df.loc[:, self.db_column_names]
            logger.debug(f"\n{df_to_upload}")
            results_chg = await Lab().update_df(self.table_name, df_to_upload)
            total_results['수정'] = results_chg
            logger.debug(f"result of changing = {results_chg}")

        self.clear_uneditable_rows()
        self.clear_new_rows()
        self.clear_editable_rows()

        return make_return_msg(total_results)

    def is_model_editing(self) -> bool:
        """
        Returns if any rows has flag column set
        :return:
        """
        return not self.model_df.loc[
            self.model_df['flag'] != RowFlags.OriginalRow, 'flag'].empty
