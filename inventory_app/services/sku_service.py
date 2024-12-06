from typing import List, Optional
from services.data_service import DataService
from db.models import SKU
from config import Config

class SkuService:
    def __init__(self):
        self.data_service = DataService()

    async def get_skus(self, item_id: Optional[int] = None) -> List[SKU]:
        return await self.data_service.get_skus(item_id)

    async def get_sku_by_id(self, sku_id: int) -> Optional[SKU]:
        return await self.data_service.get_sku_by_id(sku_id)

    async def create_sku(self, sku_data: dict) -> SKU:
        """Create a new SKU
        
        Args:
            sku_data: Dictionary containing SKU fields:
                - item_id: ID of parent item
                - root_sku: ID of root SKU (0 if this is a root)
                - sub_name: Sub name of SKU
                - active: Active status
                - sku_qty: Current quantity
                - min_qty: Minimum quantity threshold
                - expiration_date: Expiration date
                - description: Description text
                - bit_code: Bit code value
                
        Returns:
            Newly created SKU object
        """
        # Set default values if not provided
        sku_data.setdefault('root_sku', 0)
        sku_data.setdefault('active', True)
        sku_data.setdefault('sku_qty', 0)
        sku_data.setdefault('min_qty', Config.DEFAULT_MIN_QTY)
        sku_data.setdefault('description', '')
        sku_data.setdefault('bit_code', '')
        
        return await self.data_service.create_sku(sku_data) 

    async def update_sku(self, sku_id: int, sku_data: dict) -> Optional[SKU]:
        """Update existing SKU"""
        return await self.data_service.update_sku(sku_id, sku_data)

    async def delete_sku(self, sku_id: int) -> bool:
        """Delete SKU by id"""
        return await self.data_service.delete_sku(sku_id)