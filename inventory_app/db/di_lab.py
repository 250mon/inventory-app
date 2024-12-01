import re
import asyncio
from typing import List
from db.db_apis import DbApi
import pandas as pd
from common.d_logger import Logs
from constants import MAX_TRANSACTION_COUNT
from common.singleton import Singleton
from db.models import Base
from sqlalchemy import select, and_
from .models import Category, Item, SKU, User, TransactionType, Transaction


logger = Logs().get_logger("db")


class Lab(metaclass=Singleton):
    def __init__(self):
        self.db_api = DbApi()
        self.db_util = self.db_api.db_util
        self.max_transaction_count = MAX_TRANSACTION_COUNT
        self.show_inactive_items = False

        self.table_df = {
            'category': None,
            'users': None,
            'transaction_type': None,
            'items': None,
            'skus': None,
            'transactions': None
        }
        self._set_db_column_names()

        self.bool_initialized = False

    async def async_init(self):
        if self.bool_initialized is False:
            # getting dfs
            get_data = [self._get_df_from_db(table) for table
                        in self.table_df.keys()]
            data_dfs: List = await asyncio.gather(*get_data)
            for df in data_dfs:
                logger.debug(f"Retrieved DB data \n{df}")
            for table in reversed(self.table_df.keys()):
                self.table_df[table] = data_dfs.pop()

            # make reference series
            self._make_ref_series()

        self.bool_initialized = True
        return self

    def __await__(self):
        return self.async_init().__await__()

    def set_max_transaction_count(self, count: int):
        if count > 0:
            self.max_transaction_count = count
        else:
            logger.warn(f""
                        f"count({count}) is not a positive integer")

    def _set_db_column_names(self):
        self.table_column_names = {
            'items': [c.name for c in Base.metadata.tables['items'].columns],
            'skus': [c.name for c in Base.metadata.tables['skus'].columns],
            'transactions': [c.name for c in Base.metadata.tables['transactions'].columns]
        }

    async def _get_df_from_db(self, table: str, **kwargs) -> pd.DataFrame:
        current_loop = asyncio.get_event_loop()
        logger.debug(f"Current loop id in _get_df_from_db: {id(current_loop)}")
        
        logger.debug(f"Getting DataFrame for table: {table}")
        
        # Map table names to SQLAlchemy models and their required columns
        table_configs = {
            'category': (Category, [Category.category_id, Category.category_name]),
            'items': (Item, [Item.item_id, Item.active, Item.item_name, Item.category_id, Item.description]),
            'skus': (SKU, [SKU.sku_id, SKU.active, SKU.root_sku, SKU.sub_name, SKU.bit_code, 
                          SKU.sku_qty, SKU.min_qty, SKU.item_id, SKU.expiration_date, SKU.description]),
            'users': (User, [User.user_id, User.user_name, User.user_password]),
            'transaction_type': (TransactionType, [TransactionType.tr_type_id, TransactionType.tr_type]),
            'transactions': (Transaction, [Transaction.tr_id, Transaction.user_id, Transaction.sku_id,
                                         Transaction.tr_type_id, Transaction.tr_qty, Transaction.before_qty,
                                         Transaction.after_qty, Transaction.tr_timestamp, Transaction.description])
        }
        
        model, columns = table_configs[table]
        # Select specific columns explicitly
        stmt = select(*columns)
        
        # Add filters for inactive items
        if not self.show_inactive_items:
            if table == "items":
                stmt = stmt.where(Item.active == True)
            elif table == "skus":
                active_items = select(Item.item_id).where(Item.active == True)
                stmt = stmt.where(and_(
                    SKU.item_id.in_(active_items),
                    SKU.active == True
                ))
            elif table == "transactions":
                active_items = select(Item.item_id).where(Item.active == True)
                active_skus = select(SKU.sku_id).where(and_(
                    SKU.item_id.in_(active_items),
                    SKU.active == True
                ))
                stmt = stmt.where(Transaction.sku_id.in_(active_skus))

        # Handle transaction-specific queries
        if table == "transactions":
            sku_id = kwargs.get('sku_id', None)
            beg_ts = kwargs.get('beg_timestamp', '')
            end_ts = kwargs.get('end_timestamp', '')
            
            if sku_id is not None:
                stmt = stmt.where(Transaction.sku_id == sku_id)
                if beg_ts and end_ts:
                    stmt = stmt.where(and_(
                        Transaction.tr_timestamp >= beg_ts,
                        Transaction.tr_timestamp <= end_ts
                    ))
            
            stmt = stmt.order_by(Transaction.tr_id.desc()).limit(self.max_transaction_count)

        # Execute query and get results
        async with self.db_util.session() as session:
            logger.debug("Executing query...")
            result = await session.execute(stmt)
            logger.debug("Query executed")
            records = result.mappings().all()
            
        if not records:
            logger.warning(f"No records found for table: {table}")
            # Create empty DataFrame with correct column names
            column_names = [col.name for col in columns]
            return pd.DataFrame(columns=column_names)
        
        # Convert to DataFrame with explicit column names
        df = pd.DataFrame([dict(record) for record in records])
        logger.debug(f"Created DataFrame for {table} with columns: {df.columns}")
        df.fillna("", inplace=True)
        return df

    def _make_ref_series(self):
        def make_series(table, is_name=True):
            ref_df = self.table_df[table]
            logger.debug(f"Making series for {table}. DataFrame:\n{ref_df}")
            
            if ref_df.empty:
                logger.warning(f"Empty DataFrame for {table}")
                return pd.Series(dtype='object')
            
            # Get actual column names from DataFrame
            columns = list(ref_df.columns)
            logger.debug(f"Available columns for {table}: {columns}")
            
            # Map table names to column pairs (id, name)
            column_pairs = {
                'category': ('category_id', 'category_name'),
                'transaction_type': ('tr_type_id', 'tr_type'),
                'users': ('user_id', 'user_name')
            }
            
            id_col, name_col = column_pairs.get(table, (None, None))
            if not id_col or not name_col:
                logger.error(f"No column mapping found for table {table}")
                return pd.Series(dtype='object')
            
            if id_col not in columns or name_col not in columns:
                logger.error(f"Missing required columns for {table}. Need {(id_col, name_col)}, Got: {columns}")
                return pd.Series(dtype='object')
            
            try:
                if is_name:
                    return ref_df.set_index(id_col)[name_col]
                else:
                    return ref_df.set_index(name_col)[id_col]
            except Exception as e:
                logger.error(f"Error creating series for {table}: {str(e)}")
                return pd.Series(dtype='object')

        try:
            self.category_name_s = make_series('category', True)
            self.category_id_s = make_series('category', False)
            self.tr_type_s = make_series('transaction_type', True)
            self.tr_type_id_s = make_series('transaction_type', False)
            self.user_name_s = make_series('users', True)
            self.user_id_s = make_series('users', False)
        except Exception as e:
            logger.error(f"Error in _make_ref_series: {str(e)}")
            # Initialize empty series if creation fails
            self.category_name_s = pd.Series(dtype='object')
            self.category_id_s = pd.Series(dtype='object')
            self.tr_type_s = pd.Series(dtype='object')
            self.tr_type_id_s = pd.Series(dtype='object')
            self.user_name_s = pd.Series(dtype='object')
            self.user_id_s = pd.Series(dtype='object')

    async def update_lab_df_from_db(self, table: str, **kwargs):
        logger.debug(f"table {table}")
        self.table_df[table] = await self._get_df_from_db(table, **kwargs)

    async def insert_df(self, table: str, new_df: pd.DataFrame, session=None):
        return await self.db_api.insert_df(table, new_df, session)

    async def update_df(self, table: str, up_df: pd.DataFrame, session=None):
        return await self.db_api.update_df(table, up_df, session)

    async def delete_df(self, table: str, del_df: pd.DataFrame, session=None):
        return await self.db_api.delete_df(table, del_df, session)
