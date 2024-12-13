from datetime import date, datetime
from sqlalchemy import Boolean, Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import event
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class Category(Base):
    __tablename__ = 'category'
    
    category_id = Column(Integer, primary_key=True)
    category_name = Column(Text, nullable=False, unique=True)
    
    items = relationship("Item", back_populates="category", cascade="all, delete-orphan")

class Item(Base):
    __tablename__ = 'items'
    
    item_id = Column(Integer, primary_key=True)
    active = Column(Boolean, nullable=False, default=True)
    item_name = Column(Text, nullable=False, unique=True)
    category_id = Column(Integer, ForeignKey('category.category_id'), nullable=False)
    description = Column(Text)
    
    category = relationship("Category", back_populates="items")
    skus = relationship("SKU", back_populates="item", cascade="all, delete-orphan")

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
    transactions = relationship("Transaction", back_populates="sku", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    user_name = Column(Text, nullable=False, unique=True)
    user_password = Column(String, nullable=False)
    
    transactions = relationship("Transaction", back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash"""
        return check_password_hash(self.user_password, password)

# SQLAlchemy event listener to hash password before insert/update
@event.listens_for(User, 'before_insert')
@event.listens_for(User, 'before_update')
def hash_password(mapper, connection, target):
    """Hash password before saving to database"""
    if target.user_password and not target.user_password.startswith('pbkdf2:sha256:'):
        target.user_password = generate_password_hash(target.user_password)

class TransactionType(Base):
    __tablename__ = 'transaction_type'
    
    tr_type_id = Column(Integer, primary_key=True)
    tr_type = Column(Text, nullable=False, unique=True)
    
    transactions = relationship("Transaction", back_populates="transaction_type")

    # Define constants for transaction types
    BUY = 1
    SELL = 2
    ADJUSTMENT_PLUS = 3
    ADJUSTMENT_MINUS = 4

    # Map IDs to type names
    TYPE_NAMES = {
        BUY: "Buy",
        SELL: "Sell",
        ADJUSTMENT_PLUS: "Adjustment+",
        ADJUSTMENT_MINUS: "Adjustment-"
    }

    @classmethod
    def get_type_name(cls, type_id: int) -> str:
        """Get the name of a transaction type by ID"""
        return cls.TYPE_NAMES.get(type_id, "Unknown")

    @classmethod
    def is_valid_type(cls, type_id: int) -> bool:
        """Check if a transaction type ID is valid"""
        return type_id in cls.TYPE_NAMES

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

    @property
    def tr_type_name(self) -> str:
        """Get the name of the transaction type"""
        return TransactionType.get_type_name(self.tr_type_id)

    def validate_quantities(self) -> bool:
        """Validate that before_qty and after_qty are consistent with tr_qty"""
        if self.tr_type_id == TransactionType.BUY or self.tr_type_id == TransactionType.ADJUSTMENT_PLUS:
            return self.after_qty == self.before_qty + self.tr_qty
        elif self.tr_type_id == TransactionType.SELL or self.tr_type_id == TransactionType.ADJUSTMENT_MINUS:
            return self.after_qty == self.before_qty - self.tr_qty
        return False
 