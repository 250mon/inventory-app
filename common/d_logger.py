import os
import sys
import logging
import logging.config
import yaml
from common.singleton import Singleton


class Logs(metaclass=Singleton):
    def __init__(self):
        # make 'log' directory to store log files
        os.makedirs("log", exist_ok=True)

        # read config file
        with open('common/log_config.yaml', 'rt') as f:
            config = yaml.load(f, Loader=yaml.FullLoader)
            logging.config.dictConfig(config)

        self.err_logger = logging.getLogger("main")
        sys.excepthook = self.handle_exception

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        self.err_logger.error("Unexpected exception",
                              exc_info=(exc_type, exc_value, exc_traceback))
