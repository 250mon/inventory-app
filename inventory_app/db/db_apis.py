from sqlalchemy import select
from sqlalchemy.orm import selectinload
import pandas as pd
from common.d_logger import Logs
from .db_utils import DbUtil
from .models import Base, Category, Item, SKU, User, TransactionType, Transaction

logger = Logs().get_logger("db")

class DbApi:
    def __init__(self):
        self.db_util = DbUtil()

    async def create_tables(self):
        await self.db_util.create_tables()

    async def drop_tables(self):
        await self.db_util.drop_tables()

    async def initialize_db(self):
        await self.drop_tables()
        await self.create_tables()

    async def insert_df(self, table: str, new_df: pd.DataFrame):
        """Insert DataFrame records into database"""
        model_map = {
            'category': Category,
            'items': Item,
            'skus': SKU,
            'users': User,
            'transaction_type': TransactionType,
            'transactions': Transaction
        }
        
        model = model_map.get(table)
        if not model:
            logger.error(f"No model found for table: {table}")
            return False
            
        try:
            records = new_df.to_dict('records')
            logger.debug(f"Inserting records: {records}")
            
            async with self.db_util.session() as session:
                session.add_all([model(**record) for record in records])
                await session.commit()
                return True
            
        except Exception as e:
            logger.error(f"Error inserting records: {str(e)}")
            return False

    async def delete_df(self, table: str, del_df: pd.DataFrame):
        model = Base.metadata.tables[table]
        async with self.db_util.session() as session:
            col_name, id_series = next(del_df.items())
            stmt = model.delete().where(getattr(model.c, col_name).in_(id_series))
            await session.execute(stmt)
            await session.commit()

    async def update_df(self, table: str, up_df: pd.DataFrame):
        model = Base.metadata.tables[table]
        async with self.db_util.session() as session:
            for record in up_df.to_dict('records'):
                stmt = model.update().where(
                    getattr(model.c, up_df.columns[0]) == record[up_df.columns[0]]
                ).values(**{k: v for k, v in record.items() if k != up_df.columns[0]})
                await session.execute(stmt)
            await session.commit()
