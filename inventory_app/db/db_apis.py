from typing import List
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
        logger.debug(f"=== Starting DB Insert for {table} ===")
        logger.debug(f"Columns in DataFrame: {new_df.columns.tolist()}")
        logger.debug(f"Data types: {new_df.dtypes}")
        
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
            logger.debug(f"Converting DataFrame to records:")
            for record in records:
                logger.debug(f"Record to insert: {record}")
            
            async with self.db_util.session() as session:
                try:
                    session.add_all([model(**record) for record in records])
                    await session.commit()
                    logger.debug("Successfully inserted records")
                    return True
                except Exception as e:
                    logger.error(f"Database error during insert: {str(e)}")
                    logger.error(f"Error type: {type(e)}")
                    raise
            
        except Exception as e:
            logger.error(f"Error in insert_df: {str(e)}")
            logger.error(f"Error type: {type(e)}")
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

    async def delete_row(self, table: str, row_ids: List[int]):
        model = Base.metadata.tables[table]
        async with self.db_util.session() as session:
            stmt = model.delete().where(model.c.id.in_(row_ids))
            await session.execute(stmt)
            await session.commit()
