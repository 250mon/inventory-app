import sys
import pandas as pd
from typing import Dict
from PySide6.QtWidgets import QTableView, QApplication
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from constants import EditLevel
from common.d_logger import Logs



logger = Logs().get_logger("main")


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    SortRole = Qt.UserRole + 1

    def __init__(self, dataframe: pd.DataFrame = None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.model_df = dataframe
        self.edit_level = EditLevel.UserModifiable
        self.is_editable = False
        self.new_rows_set = set()
        self.editable_rows_set = set()
        self.uneditable_rows_set = set()

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self.model_df)

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self.model_df.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return str(self.model_df.iloc[index.row(), index.column()])
        elif role == Qt.EditRole:
            return str(self.model_df.iloc[index.row(), index.column()])

        return None

    def headerData(self,
                   section: int,
                   orientation: Qt.Orientation,
                   role=Qt.ItemDataRole) -> str or None:
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.model_df.columns[section])

            if orientation == Qt.Vertical:
                return str(self.model_df.index[section])

        return None

    def setData(self,
                index: QModelIndex,
                value: object,
                role=Qt.EditRole):
        if not index.isValid():
            return False

        if role == Qt.EditRole:
            self.model_df.iloc[index.row(), index.column()] = value
            self.dataChanged.emit(index, index)
            return True
        else:
            return False

    def flags(self, index: QModelIndex):
        if not index.isValid():
            logger.debug(f"CHECK!!! index({index}) is not valid")
            return Qt.NoItemFlags

        if not self.is_editable:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.row() in self.uneditable_rows_set:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        elif (index.row() in self.new_rows_set and
                self.col_idx_edit_lvl[index.column()] <= EditLevel.Creatable):
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable
        elif self.col_idx_edit_lvl[index.column()] <= self.edit_level:
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_edit_level(self, level: EditLevel):
        self.edit_level = level

    def set_column_index_edit_level(self, col_idx_edit_level: Dict[int, EditLevel]):
        self.col_idx_edit_lvl = col_idx_edit_level

    def set_editable(self, is_editable: bool):
        self.is_editable= is_editable

    def set_editable_row(self, row: int):
        logger.debug(f"row{row} => "
                     f'editable_rows_{self.editable_rows_set}')
        self.editable_rows_set.add(row)

    def unset_editable_row(self, row: int):
        logger.debug(f"row{row} from "
                     f'editable_rows_{self.editable_rows_set}')
        if row in self.editable_rows_set:
            self.editable_rows_set.remove(row)
        else:
            logger.warn(f"unset_editable_row: cannot find "
                        f'row {row} int the set')

    def clear_editable_rows(self):
        if len(self.editable_rows_set) > 0:
            logger.debug(f"remove all rows from "
                         f'editable_rows_{self.editable_rows_set}')
            self.editable_rows_set.clear()

    def set_new_row(self, row: int):
        """
        Makes every column editable for new rows
        :param row:
        :return:
        """
        logger.debug(f"row{row} => new_rows_{self.new_rows_set}")
        self.new_rows_set.add(row)

    def unset_new_row(self, row: int):
        logger.debug(f"remove row {row} from "
                     f'new_rows_{self.new_rows_set}')
        if row in self.new_rows_set:
            self.new_rows_set.remove(row)
        else:
            logger.warn(f"unset_editable_new_row: cannot find row {row} int the set")

    def clear_new_rows(self):
        if len(self.new_rows_set) > 0:
            self.new_rows_set.clear()
            logger.debug(f"set_editable_new_row : clearing")

    def set_uneditable_row(self, row: int):
        """
        Makes every column uneditable for deleted rows
        :param row:
        :return:
        """
        logger.debug(f"row{row} => "
                     f'uneditable_rows_{self.uneditable_rows_set}')
        self.uneditable_rows_set.add(row)

    def unset_uneditable_row(self, row: int):
        logger.debug(f"remove row {row} from "
                     f'uneditable_rows_{self.uneditable_rows_set}')
        if row in self.uneditable_rows_set:
            self.uneditable_rows_set.remove(row)
        else:
            logger.warn(f"unset_uneditable_row: cannot find row {row} int the set")

    def clear_uneditable_rows(self):
        if len(self.uneditable_rows_set) > 0:
            logger.debug(f"remove all rows from "
                         f'uneditable_rows_{self.uneditable_rows_set}')
            self.uneditable_rows_set.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    df = pd.read_csv("iris.csv")

    view = QTableView()
    view.resize(800, 500)
    view.horizontalHeader().setStretchLastSection(True)
    view.setAlternatingRowColors(True)
    view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

    model = PandasModel(df)
    view.setModel(model)
    view.show()
    app.exec()
