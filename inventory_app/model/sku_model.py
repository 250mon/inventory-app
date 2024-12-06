from PySide6.QtCore import Qt, QModelIndex, Slot, QDate
from PySide6.QtGui import QColor
from typing import List, Dict, Optional
from model.sql_model import SQLTableModel
from model.item_model import ItemModel
from services.sku_service import SkuService
from config import Config
from common.d_logger import Logs
from common.datetime_utils import pydate_to_qdate, qdate_to_pydate

logger = Logs().get_logger("main")

class SkuModel(SQLTableModel):
    def __init__(self, user_name: str, sku_service: SkuService, item_model: ItemModel):
        super().__init__()
        self.user_name = user_name
        self._service = sku_service
        self.item_model = item_model
        self.selected_upper_id = None
        self.init_params()
        self.item_model.item_model_changed_signal.connect(self.item_model_changed)

    def init_params(self):
        """Initialize model parameters"""
        self._headers = [
            'sku_id', 'root_sku', 'item_name', 'sub_name',
            'active', 'sku_qty', 'min_qty', 'expiration_date',
            'description', 'bit_code', 'sku_name', 'item_id', 'flag'
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'sku_id': Config.EditLevel.NotEditable,
            'root_sku': Config.EditLevel.Creatable,
            'item_name': Config.EditLevel.NotEditable,
            'sub_name': Config.EditLevel.UserModifiable,
            'active': Config.EditLevel.AdminModifiable,
            'sku_qty': Config.EditLevel.AdminModifiable,
            'min_qty': Config.EditLevel.UserModifiable,
            'expiration_date': Config.EditLevel.Creatable,
            'description': Config.EditLevel.UserModifiable,
            'bit_code': Config.EditLevel.AdminModifiable,
            'sku_name': Config.EditLevel.NotEditable,
            'item_id': Config.EditLevel.NotEditable,
            'flag': Config.EditLevel.NotEditable
        }

    async def load_data(self):
        """Load SKUs from service"""
        self._data = await self._service.get_skus(self.selected_upper_id)
        self._update_sku_names()
        self.layoutChanged.emit()

    def _update_sku_names(self):
        """Update SKU names using item names"""
        for sku in self._data:
            item_name = self.item_model._data[
                next(i for i, item in enumerate(self.item_model._data) 
                    if item.item_id == sku.item_id)
            ].item_name
            setattr(sku, 'item_name', item_name)
            setattr(sku, 'sku_name', f"{item_name} {sku.sub_name}".strip())

    def get_default_delegate_info(self) -> List[int]:
        """Returns column indexes for default delegate"""
        return [self.get_col_number(c) for c in ['sub_name', 'description', 'bit_code']]

    def get_combobox_delegate_info(self) -> Dict[int, List]:
        """Returns column indexes and values for combobox delegate"""
        return {
            self.get_col_number('active'): ['Y', 'N'],
        }

    def get_spinbox_delegate_info(self) -> Dict[int, List]:
        """Returns column indexes and ranges for spinbox delegate"""
        return {
            self.get_col_number('min_qty'): [0, 1000],
        }

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        if not index.isValid():
            return None

        row = self._data[index.row()]
        col_name = self.get_col_name(index.column())

        if role == Qt.DisplayRole or role == Qt.EditRole or role == self.SortRole:
            if col_name in ['sku_id', 'root_sku', 'item_id', 'sku_qty', 'min_qty']:
                return getattr(row, col_name)
            elif col_name == 'active':
                return 'Y' if getattr(row, col_name) else 'N'
            elif col_name == 'expiration_date':
                return pydate_to_qdate(getattr(row, col_name))
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
            if col_name == 'active':
                setattr(row, col_name, value == 'Y')
            elif col_name == 'expiration_date':
                if isinstance(value, QDate):
                    value = qdate_to_pydate(value)
                setattr(row, col_name, value)
            elif col_name == 'root_sku':
                # Validate root_sku
                if not self._validate_root_sku(value, row.item_id):
                    return False
                setattr(row, col_name, value)
            elif col_name == 'sub_name':
                setattr(row, col_name, value)
                self._update_sku_names()  # Update sku_name when sub_name changes
            else:
                setattr(row, col_name, value)

            self.dataChanged.emit(index, index)
            return True

        except Exception as e:
            logger.error(f"Error setting data: {e}")
            return False

    def _validate_root_sku(self, root_sku: int, item_id: int) -> bool:
        """Validate root SKU belongs to same item"""
        if root_sku == 0:
            return True
        root_row = next((sku for sku in self._data if sku.sku_id == root_sku), None)
        return root_row is not None and root_row.item_id == item_id

    def set_upper_model_id(self, item_id: Optional[int]):
        """Set selected item ID for filtering"""
        self.selected_upper_id = item_id
        logger.debug(f"item_id({self.selected_upper_id}) is set")

    def is_sku_qty_correct(self, sku_id: int, sku_qty: int) -> bool:
        """Check if SKU quantity is correct for root SKU"""
        sub_skus = [sku for sku in self._data if sku.root_sku == sku_id]
        if not sub_skus:
            return True
        return sku_qty == sum(sku.sku_qty for sku in sub_skus)

    def is_active_row(self, index: QModelIndex) -> bool:
        if not index.isValid():
            return False
        row = self._data[index.row()]
        item_active = self.item_model.is_active_row(
            next(i for i, item in enumerate(self.item_model._data) 
                if item.item_id == row.item_id)
        )
        return item_active and row.active

    def cell_color(self, index: QModelIndex) -> QColor:
        if not index.isValid():
            return QColor(Qt.white)

        row = self._data[index.row()]
        col_name = self.get_col_name(index.column())

        if col_name == "sku_qty":
            if row.root_sku == 0 and not self.is_sku_qty_correct(row.sku_id, row.sku_qty):
                return QColor(255, 180, 150, 50)
            elif row.sku_qty < row.min_qty:
                return QColor(Qt.red)

        return super().cell_color(index)

    async def save_changes(self):
        """Save changes to database"""
        for row in self._data:
            if getattr(row, 'flag', None) == Config.RowFlags.NewRow:
                # For new SKUs, include all fields except sku_id
                sku_data = self.get_clean_data(row, exclude_fields=['sku_id'])
                await self._service.create_sku(sku_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.ChangedRow:
                # For updates, exclude unchangeable fields
                sku_data = self.get_clean_data(row, exclude_fields=['sku_id', 'item_id'])
                await self._service.update_sku(row.sku_id, sku_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.DeletedRow:
                await self._service.delete_sku(row.sku_id)

        await self.load_data()

    @Slot(object)
    def item_model_changed(self, item_ids: List):
        """Handle changes in item model"""
        self._update_sku_names()
        self.layoutChanged.emit()