from typing import List, Optional
from services.data_service import DataService
from db.models import User

class UserService:
    def __init__(self):
        self.data_service = DataService()

    async def get_users(self) -> List[User]:
        return await self.data_service.get_users()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        return await self.data_service.get_user_by_id(user_id)

    async def get_user_by_name(self, username: str) -> Optional[User]:
        return await self.data_service.get_user_by_name(username)

    async def create_user(self, user_data: dict) -> User:
        return await self.data_service.create_user(user_data)

    async def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        return await self.data_service.update_user(user_id, user_data)

    async def delete_user(self, user_id: int) -> bool:
        return await self.data_service.delete_user(user_id)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user by username and password"""
        user = await self.get_user_by_name(username)
        if user and user.verify_password(password):  # Assuming password verification is handled in User model
            return user
        return None

    async def change_password(self, user_id: int, new_password: str) -> bool:
        """Change a user's password"""
        user = await self.get_user_by_id(user_id)
        if user:
            user_data = {'user_password': new_password}  # Password hashing should be handled in User model
            await self.update_user(user_id, user_data)
            return True
        return False 