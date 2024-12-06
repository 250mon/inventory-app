from typing import List, Optional
from datetime import datetime
from services.data_service import DataService
from db.models import Transaction

class TransactionService:
    def __init__(self):
        self.data_service = DataService()

    async def get_transactions(
        self,
        sku_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Transaction]:
        return await self.data_service.get_transactions(sku_id, start_date, end_date)

    async def get_transaction_by_id(self, tr_id: int) -> Optional[Transaction]:
        return await self.data_service.get_transaction_by_id(tr_id)

    async def create_transaction(self, tr_data: dict) -> Transaction:
        """Create new transaction"""
        # Set default values
        tr_data.setdefault('tr_timestamp', datetime.now())
        tr_data.setdefault('description', '')
        
        return await self.data_service.create_transaction(tr_data)

    async def update_transaction(self, tr_id: int, tr_data: dict) -> Optional[Transaction]:
        """Update existing transaction"""
        return await self.data_service.update_transaction(tr_id, tr_data)

    async def delete_transaction(self, tr_id: int) -> bool:
        """Delete transaction"""
        return await self.data_service.delete_transaction(tr_id)
 