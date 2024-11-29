CREATE_CATEGORY_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS category(
        category_id SERIAL PRIMARY KEY,
        category_name TEXT NOT NULL,
        UNIQUE(category_name)
    );"""

CREATE_ITEM_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS items(
        item_id SERIAL PRIMARY KEY,
        active BOOL NOT NULL DEFAULT TRUE,
        item_name TEXT NOT NULL,
        category_id INT NOT NULL,
        description TEXT,
        FOREIGN KEY (category_id) REFERENCES category(category_id),
        UNIQUE(item_name)
    );"""

CREATE_SKU_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS skus(
        sku_id SERIAL PRIMARY KEY,
        active BOOL NOT NULL DEFAULT TRUE,
        root_sku INT NOT NULL DEFAULT 0,
        sub_name TEXT,
        bit_code TEXT,
        sku_qty INT NOT NULL,
        min_qty INT NOT NULL DEFAULT 2,
        item_id INT NOT NULL,
        expiration_date DATE NOT NULL DEFAULT '9999-01-01',
        description TEXT,
        FOREIGN KEY (item_id) REFERENCES items(item_id),
        UNIQUE(item_id, sub_name, expiration_date)
    );"""

CREATE_USER_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id SERIAL PRIMARY KEY,
        user_name TEXT NOT NULL,
        user_password BYTEA NOT NULL,
        UNIQUE(user_name)
    );"""

CREATE_TRANSACTION_TYPE_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS transaction_type(
        tr_type_id SERIAL PRIMARY KEY,
        tr_type TEXT NOT NULL,
        UNIQUE(tr_type)
    );"""

CREATE_TRANSACTION_TABLE = \
    """
    CREATE TABLE IF NOT EXISTS transactions(
        tr_id SERIAL PRIMARY KEY,
        user_id INT NOT NULL,
        sku_id INT NOT NULL,
        tr_type_id INT NOT NULL,
        tr_qty INT NOT NULL,
        before_qty INT NOT NULL,
        after_qty INT NOT NULL,
        tr_timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (tr_type_id) REFERENCES transaction_type(tr_type_id)
    );"""
