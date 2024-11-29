from enum import Enum
from functools import total_ordering
from operator import methodcaller
from common.singleton import Singleton

CONFIG_FILE = 'di_config'
ADMIN_GROUP = ['admin', 'jye']
MAX_TRANSACTION_COUNT = 10
DEFAULT_MIN_QTY = 1


class UserPrivilege:
    Admin = 0
    User = 1


class RowFlags:
    OriginalRow = 0
    NewRow = 1
    ChangedRow = 2
    DeletedRow = 4


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


class ConfigReader(metaclass=Singleton):
    def __init__(self):
        self.options = {}

    def read_config_file(self, file_path):
        try:
            with open(file_path, 'r') as fd:
                # strip lines
                lines = map(methodcaller("strip"), fd.readlines())
                # filtering lines starting with '#' or blank lines
                lines_filtered = filter(lambda l: l and not l.startswith("#"), lines)
                # parsing
                words_iter = map(methodcaller("split", "="), lines_filtered)
                # converting map obj to dict
                self.options = {k.strip(): v.strip() for k, v in words_iter}

        except Exception as e:
            print(e)

    def get_options(self, option_name: str):
        options = self.options.get(option_name, None)
        if options is None:
            self.read_config_file(CONFIG_FILE)
            options = self.options.get(option_name, None)
        return options
