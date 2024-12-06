from typing import List, Optional
from services.data_service import DataService
from db.models import Item

class ItemService:
    def __init__(self):
        self.data_service = DataService()

    async def get_items(self, include_inactive: bool = False) -> List[Item]:
        return await self.data_service.get_items(include_inactive)

    async def create_item(self, item_data: dict) -> Item:
        return await self.data_service.create_item(item_data)

    async def update_item(self, item_id: int, item_data: dict) -> Optional[Item]:
        return await self.data_service.update_item(item_id, item_data)

    async def delete_item(self, item_id: int) -> bool:
        return await self.data_service.delete_item(item_id) 