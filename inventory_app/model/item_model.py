from PySide6.QtCore import Qt, QModelIndex, Signal
from model.sql_model import SQLTableModel
from services.item_service import ItemService
from model.category_model import CategoryModel
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")

class ItemModel(SQLTableModel):
    item_model_changed_signal = Signal(object)

    def __init__(self, user_name: str, item_service: ItemService, category_model: CategoryModel):
        super().__init__()
        self.user_name = user_name
        self._service = item_service
        self._category_model = category_model
        self._setup_model()

    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = [
            'item_id', 'active', 'item_name', 'category_name',
            'description', 'category_id', 'flag'
        ]
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'item_id': Config.EditLevel.NotEditable,
            'active': Config.EditLevel.AdminModifiable,
            'item_name': Config.EditLevel.AdminModifiable,
            'category_name': Config.EditLevel.UserModifiable,
            'description': Config.EditLevel.UserModifiable,
            'category_id': Config.EditLevel.NotEditable,
            'flag': Config.EditLevel.NotEditable
        }

    async def load_data(self):
        """Load items from service"""
        self._data = await self._service.get_items()
        self.layoutChanged.emit()

    def get_default_delegate_info(self) -> List[int]:
        """Returns column indexes for default delegate"""
        return [self.get_col_number(c) for c in ['item_name', 'description']]

    def get_combobox_delegate_info(self) -> Dict[int, List]:
        """Returns column indexes and values for combobox delegate"""
        return {
            self.get_col_number('active'): ['Y', 'N'],
            self.get_col_number('category_name'): self._category_model.get_category_names()
        }

    def data(self, index: QModelIndex, role=Qt.DisplayRole) -> object:
        if not index.isValid():
            return None

        row = self._data[index.row()]
        col_name = self.get_col_name(index.column())

        if role == Qt.DisplayRole or role == Qt.EditRole or role == self.SortRole:
            if col_name == 'item_id' or col_name == 'category_id':
                return getattr(row, col_name)
            elif col_name == 'active':
                return 'Y' if getattr(row, col_name) else 'N'
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
            elif col_name == 'category_name':
                # Find category_id using CategoryModel
                category = self._category_model.get_category_by_name(value)
                if category:
                    setattr(row, 'category_id', category.category_id)
                    setattr(row, col_name, value)
            elif col_name == 'item_name':
                # Check for duplicates
                if any(item.item_name == value for item in self._data if item != row):
                    logger.debug(f"item name({value}) is already in use")
                    return False
                setattr(row, col_name, value)
            else:
                setattr(row, col_name, value)

            self.dataChanged.emit(index, index)
            return True

        except Exception as e:
            logger.error(f"Error setting data: {e}")
            return False

    async def save_changes(self):
        """Save changes to database"""
        for row in self._data:
            if getattr(row, 'flag', None) == Config.RowFlags.NewRow:
                # For new items, include all fields except item_id
                item_data = self.get_clean_data(row, exclude_fields=['item_id'])
                await self._service.create_item(item_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.ChangedRow:
                # For updates, exclude unchangeable fields
                item_data = self.get_clean_data(row, exclude_fields=['item_id'])
                await self._service.update_item(row.item_id, item_data)
            elif getattr(row, 'flag', None) == Config.RowFlags.DeletedRow:
                await self._service.delete_item(row.item_id)

        await self.load_data()

    def is_active_row(self, index: QModelIndex) -> bool:
        if not index.isValid():
            return False
        return bool(self._data[index.row()].active)

    def validate_new_row(self, index: QModelIndex) -> bool:
        """Validate a new row"""
        if not index.isValid():
            return False
            
        row = self._data[index.row()]
        if not row.item_name:
            return False
            
        # Check for duplicate item names
        return not any(item.item_name == row.item_name 
                      for item in self._data 
                      if item != row)

    def get_user_privilege(self) -> Config.UserPrivilege:
        """Get user privilege level"""
        # This should be implemented based on your user management system
        return Config.UserPrivilege.Admin if self.user_name == "admin" else Config.UserPrivilege.User
