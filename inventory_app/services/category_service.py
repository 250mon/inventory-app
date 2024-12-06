from typing import List, Optional
from services.data_service import DataService
from db.models import Category

class CategoryService:
    def __init__(self):
        self.data_service = DataService()

    async def get_categories(self) -> List[Category]:
        return await self.data_service.get_categories()

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        return await self.data_service.get_category_by_id(category_id)

    async def create_category(self, category_data: dict) -> Category:
        return await self.data_service.create_category(category_data)

    async def update_category(self, category_id: int, category_data: dict) -> Optional[Category]:
        return await self.data_service.update_category(category_id, category_data)

    async def delete_category(self, category_id: int) -> bool:
        return await self.data_service.delete_category(category_id) 