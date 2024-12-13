from PySide6.QtCore import Signal
from sqlalchemy import select
from typing import List, Optional
from model.sql_model import SQLTableModel
from model.base_model import BaseDBModel
from model.models import User
from config import Config
from common.d_logger import Logs

logger = Logs().get_logger("main")

class UserModel(SQLTableModel, BaseDBModel):
    user_model_changed_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self._setup_model()

    def _setup_model(self):
        """Initialize model parameters"""
        self._headers = ['user_id', 'user_name', 'user_password']
        self._column_map = {col: idx for idx, col in enumerate(self._headers)}
        
        self.col_edit_lvl = {
            'user_id': Config.EditLevel.NotEditable,
            'user_name': Config.EditLevel.AdminModifiable,
            'user_password': Config.EditLevel.AdminModifiable
        }

    # CRUD Operations
    async def create_user(self, user_data: dict) -> User:
        """Create a new user in the database"""
        async with self.session() as session:
            user = User(**user_data)
            session.add(user)
            await session.flush()
            await session.refresh(user)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID"""
        async with self.session() as session:
            return await session.get(User, user_id)

    async def get_user_by_name(self, username: str) -> Optional[User]:
        """Get a user by username"""
        async with self.session() as session:
            result = await session.execute(
                select(User).where(User.user_name == username)
            )
            return result.scalar_one_or_none()

    async def get_all_users(self) -> List[User]:
        """Get all users"""
        async with self.session() as session:
            result = await session.execute(select(User))
            return result.scalars().all()

    async def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        """Update an existing user"""
        async with self.session() as session:
            user = await session.get(User, user_id)
            if user:
                for key, value in user_data.items():
                    setattr(user, key, value)
                await session.flush()
                await session.refresh(user)
                return user
            return None

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user"""
        async with self.session() as session:
            user = await session.get(User, user_id)
            if user:
                await session.delete(user)
                return True
            return False

    # Qt Model Methods
    async def load_data(self):
        """Load users for the Qt model"""
        self._data = await self.get_all_users()
        self.layoutChanged.emit()

    def validate_user(self, username: str, exclude_id: Optional[int] = None) -> bool:
        """Validate user data"""
        if not username:
            return False
            
        # Check for duplicate usernames
        return not any(user.user_name == username 
                      for user in self._data 
                      if user.user_id != exclude_id)

    def create_empty_user(self) -> User:
        """Create a new empty user object"""
        return User(
            user_id=0,  # Temporary ID
            user_name='',
            user_password=''
        )

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password"""
        user = await self.get_user_by_name(username)
        if user and user.verify_password(password):  # Assuming password verification is handled in User model
            return user
        return None

    async def change_password(self, user_id: int, new_password: str) -> bool:
        """Change a user's password"""
        user = await self.get_user(user_id)
        if user:
            user_data = {'user_password': new_password}  # Password hashing should be handled in User model
            await self.update_user(user_id, user_data)
            return True
        return False 