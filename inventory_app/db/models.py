from datetime import date, datetime
from sqlalchemy import Boolean, Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Category(Base):
    __tablename__ = 'category'
    
    category_id = Column(Integer, primary_key=True)
    category_name = Column(Text, nullable=False, unique=True)
    
    items = relationship("Item", back_populates="category")

class Item(Base):
    __tablename__ = 'items'
    
    item_id = Column(Integer, primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    item_name = Column(Text, nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey('category.category_id'), nullable=False)
    description = Column(Text)
    
    category = relationship("Category", back_populates="items")
    skus = relationship("SKU", back_populates="item")

class SKU(Base):
    __tablename__ = 'skus'
    
    sku_id = Column(Integer, primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    root_sku = Column(Integer, nullable=False, default=0)
    sub_name = Column(Text)
    bit_code = Column(Text)
    sku_qty = Column(Integer, nullable=False)
    min_qty = Column(Integer, nullable=False, default=2)
    item_id = Column(Integer, ForeignKey('items.item_id'), nullable=False)
    expiration_date = Column(Date, nullable=False, default=date(9999, 1, 1))
    description = Column(Text)
    
    item = relationship("Item", back_populates="skus")
    transactions = relationship("Transaction", back_populates="sku")

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    user_name = Column(Text, nullable=False, unique=True)
    user_password = Column(String, nullable=False)
    
    transactions = relationship("Transaction", back_populates="user")

class TransactionType(Base):
    __tablename__ = 'transaction_type'
    
    tr_type_id = Column(Integer, primary_key=True)
    tr_type = Column(Text, nullable=False, unique=True)
    
    transactions = relationship("Transaction", back_populates="transaction_type")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    tr_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    sku_id = Column(Integer, ForeignKey('skus.sku_id'), nullable=False)
    tr_type_id = Column(Integer, ForeignKey('transaction_type.tr_type_id'), nullable=False)
    tr_qty = Column(Integer, nullable=False)
    before_qty = Column(Integer, nullable=False)
    after_qty = Column(Integer, nullable=False)
    tr_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(Text)
    
    user = relationship("User", back_populates="transactions")
    sku = relationship("SKU", back_populates="transactions")
    transaction_type = relationship("TransactionType", back_populates="transactions") 