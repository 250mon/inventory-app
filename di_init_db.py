import asyncio
import pandas as pd
import bcrypt
from db.db_apis import DbApi
from db.inventory_schema import *


async def insert_initial_data(db_api):
    initial_data = {}

    # initial insert
    initial_data['category'] = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['외용제', '수액제', '보조기', '기타']
    })

    initial_data['transaction_type'] = pd.DataFrame({
        'id': [1, 2, 3, 4],
        'name': ['Buy', 'Sell', 'AdjustmentPlus', 'AdjustmentMinus']
    })

    def encrypt_password(password):
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password

    encrypted_pw = encrypt_password('a')
    initial_data['users'] = pd.DataFrame({
        'id': [1, 2],
        'name': ['admin', 'test'],
        'pw': [encrypted_pw, encrypted_pw]
    })

    initial_data['items'] = pd.DataFrame({
        'item_id': ['DEFAULT', 'DEFAULT'],
        'active': [True, True],
        'item_name': ['노시셉톨', '써지겔'],
        'category_id': [1, 1],
        'description': ['', '']
    })

    initial_data['skus'] = pd.DataFrame({
        'sku_id': ['DEFAULT', 'DEFAULT', 'DEFAULT'],
        'active': [True, True, True],
        'root_sku': [0, 0, 0],
        'sub_name': ['40ml', '120ml', ''],
        'bit_code': ['noci40', 'noci120', 'surgigel'],
        'sku_qty': [0, 0, 0],
        'min_qty': [1, 1, 1],
        'item_id': [1, 1, 2],
        'expiration_date': ['DEFAULT', 'DEFAULT', 'DEFAULT'],
        'description': ['', '', '']
    })

    initial_data['transactions'] = pd.DataFrame({
        'tr_id': ['DEFAULT'],
        'user_id': [1],
        'sku_id': [1],
        'tr_type_id': [1],
        'tr_qty': [0],
        'before_qty': [0],
        'after_qty': [0],
        'tr_timestamp': ['DEFAULT'],
        'description': ['']
    })

    for table, data_df in initial_data.items():
        # make dataframe for each table
        await db_api.insert_df(table, data_df)

async def main():
    db_api = DbApi()

    # Initialize db by dropping all the tables and then
    # creating them all over again.
    statements = [CREATE_CATEGORY_TABLE,
                  CREATE_ITEM_TABLE,
                  CREATE_SKU_TABLE,
                  CREATE_USER_TABLE,
                  CREATE_TRANSACTION_TYPE_TABLE,
                  CREATE_TRANSACTION_TABLE]
    await db_api.initialize_db(statements)

    # After creating the tables, inserting initial data
    await insert_initial_data(db_api)


if __name__ == '__main__':
    asyncio.run(main())
