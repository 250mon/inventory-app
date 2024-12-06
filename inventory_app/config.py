# config.py
import os
from dotenv import load_dotenv
from enum import Enum
from functools import total_ordering

# Load environment variables from .env file
load_dotenv()

class Config:
    # Determine if running in test mode
    TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'

    # Database configuration
    DB_HOST = os.getenv('TEST_DB_HOST') if TEST_MODE else os.getenv('DB_HOST')
    DB_PORT = os.getenv('TEST_DB_PORT') if TEST_MODE else os.getenv('DB_PORT')
    DB_USER = os.getenv('TEST_DB_USER') if TEST_MODE else os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('TEST_DB_PASSWORD') if TEST_MODE else os.getenv('DB_PASSWORD')
    DB_NAME = os.getenv('TEST_DB_NAME') if TEST_MODE else os.getenv('DB_NAME')

    # Application configuration
    ADMIN_GROUP = os.getenv('ADMIN_GROUP').split(',')
    MAX_TRANSACTION_COUNT = int(os.getenv('MAX_TRANSACTION_COUNT'))
    DEFAULT_MIN_QTY = int(os.getenv('DEFAULT_MIN_QTY'))

    # Row flags
    class RowFlags:
        OriginalRow = 0
        NewRow = 1
        ChangedRow = 2
        DeletedRow = 4

    # Edit levels
    @total_ordering
    class EditLevel(Enum):
        UserModifiable = 1
        AdminModifiable = 2
        Creatable = 3
        NotEditable = 5

        def __lt__(self, other):
            if self.__class__ is other.__class__:
                return self.value < other.value
            return NotImplemented

    # User privilege levels
    class UserPrivilege(Enum):
        User = 1
        Admin = 2