from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QDateTime
from typing import List, Dict, Optional
from datetime import datetime
from model.sql_model import SQLTableModel
from model.sku_model import SkuModel
from services.transaction_service import TransactionService
from config import Config
from common.d_logger import Logs
from common.datetime_utils import pydt_to_qdt, qdt_to_pydt

logger = Logs().get_logger("main")

class TrModel(SQLTableModel):
    def __init__(self, user_name: str, transaction_service: TransactionService, sku_model: SkuModel):
        super().__init__()
        self.user_name = user_name
        self._service = transaction_service
        self.sku_model = sku_model
        self.selected_upper_id = None
        self.selected_upper_name = ""
        self.beg_timestamp = None
        self.end_timestamp = None
        self.init_params()

    def init_params(self):
        """Initialize model parameters"""
        self._headers = [
            'tr_id', 'sku_id', 'tr_type', 'tr_qty',
            'before_qty', 'after_qty', 'tr_timestamp',
            'description', 'user_name', 'tr_type_id',
            'user_id', 'flag'
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'tr_id': Config.EditLevel.NotEditable,
            'sku_id': Config.EditLevel.NotEditable,
            'tr_type': Config.EditLevel.Creatable,
            'tr_qty': Config.EditLevel.Creatable,
            'before_qty': Config.EditLevel.NotEditable,
            'after_qty': Config.EditLevel.NotEditable,
            'tr_timestamp': Config.EditLevel.NotEditable,
            'description': Config.EditLevel.UserModifiable,
            'user_name': Config.EditLevel.NotEditable,
            'tr_type_id': Config.EditLevel.NotEditable,
            'user_id': Config.EditLevel.NotEditable,
            'flag': Config.EditLevel.NotEditable
        }

    async def load_data(self):
        """Load transactions from service"""
        self._data = await self._service.get_transactions(
            self.selected_upper_id,
            self.beg_timestamp,
            self.end_timestamp
        )
        self.layoutChanged.emit()

    def get_default_delegate_info(self) -> List[int]:
        """Returns column indexes for default delegate"""
        return [self.get_col_number('description')]

    def get_combobox_delegate_info(self) -> Dict[int, List]:
        """Returns column indexes and values for combobox delegate"""
        return {
            self.get_col_number('tr_type'): ['Buy', 'Sell', 'AdjustmentPlus', 'AdjustmentMinus']
        }

    def get_spinbox_delegate_info(self) -> Dict[int, List]:
        """Returns column indexes and ranges for spinbox delegate"""
        return {
            self.get_col_number('tr_qty'): [1, 1000],
        }

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        if not index.isValid():
            return None

        row = self._data[index.row()]
        col_name = self.get_col_name(index.column())

        if role == Qt.DisplayRole or role == Qt.EditRole or role == self.SortRole:
            if col_name in ['tr_id', 'user_id', 'sku_id', 'tr_type_id',
                           'tr_qty', 'before_qty', 'after_qty']:
                return getattr(row, col_name)
            elif col_name == 'tr_timestamp':
                return pydt_to_qdt(getattr(row, col_name))
            else:
                return str(getattr(row, col_name))

        elif role == Qt.TextAlignmentRole:
            return Qt.AlignLeft if col_name == 'description' else Qt.AlignCenter

        return None

    def setData(self, index: QModelIndex, value: object, role=Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False

        row = self._data[index.row()]
        col_name = self.get_col_name(index.column())

        try:
            if col_name == 'tr_type':
                tr_type_map = {'Buy': 1, 'Sell': 2, 'AdjustmentPlus': 3, 'AdjustmentMinus': 4}
                setattr(row, 'tr_type_id', tr_type_map[value])
                setattr(row, col_name, value)
            elif col_name == 'tr_timestamp':
                if isinstance(value, QDateTime):
                    value = qdt_to_pydt(value)
                setattr(row, col_name, value)
            else:
                setattr(row, col_name, value)

            if col_name == 'tr_qty':
                self._update_quantities(row)

            self.dataChanged.emit(index, index)
            return True

        except Exception as e:
            logger.error(f"Error setting data: {e}")
            return False

    def _update_quantities(self, row):
        """Update before/after quantities based on transaction type"""
        sku = next((s for s in self.sku_model._data if s.sku_id == row.sku_id), None)
        if not sku:
            return

        row.before_qty = sku.sku_qty
        if row.tr_type in ['Buy', 'AdjustmentPlus']:
            row.after_qty = row.before_qty + row.tr_qty
        else:
            row.after_qty = row.before_qty - row.tr_qty

    def set_upper_model_id(self, sku_id: Optional[int]):
        """Set selected SKU ID for filtering"""
        self.selected_upper_id = sku_id
        if sku_id is not None:
            sku = next((s for s in self.sku_model._data if s.sku_id == sku_id), None)
            self.selected_upper_name = sku.sku_name if sku else ""
        else:
            self.selected_upper_name = ""
        logger.debug(f"sku_id({self.selected_upper_id}) is set")

    def set_date_range(self, beg: datetime, end: datetime):
        """Set date range for filtering transactions"""
        self.beg_timestamp = beg
        self.end_timestamp = end
        logger.debug(f"date range: {beg} - {end}")

    async def save_changes(self):
        """Save changes to database"""
        for row in self._data:
            if getattr(row, 'flag', None) == Config.RowFlags.NewRow:
                # For new transactions, exclude tr_id
                tr_data = self.get_clean_data(row, exclude_fields=['tr_id'])
                await self._service.create_transaction(tr_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.ChangedRow:
                # For updates, only include editable fields
                tr_data = self.get_clean_data(row, exclude_fields=[
                    'tr_id', 'sku_id', 'tr_timestamp', 'user_id', 'user_name'
                ])
                await self._service.update_transaction(row.tr_id, tr_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.DeletedRow:
                await self._service.delete_transaction(row.tr_id)

        await self.load_data()

        # Update SKU quantities
        if self.selected_upper_id is not None:
            sku = next((s for s in self.sku_model._data if s.sku_id == self.selected_upper_id), None)
            if sku and self._data:
                last_tr = max(self._data, key=lambda x: x.tr_timestamp)
                sku.sku_qty = last_tr.after_qty
