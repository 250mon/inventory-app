import os
import sys
import logging
import logging.config
import yaml
from common.singleton import Singleton


class Logs(metaclass=Singleton):
    def __init__(self):
        # Get the absolute path to the directory containing d_logger.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_config_path = os.path.join(current_dir, 'log_config.yaml')
        
        with open(log_config_path, 'rt') as f:
            config = yaml.safe_load(f)
        
        # Modify the log file paths to be absolute
        logs_dir = os.path.join(os.path.dirname(current_dir), 'logs')
        os.makedirs(logs_dir, exist_ok=True)  # Create logs directory if it doesn't exist
        
        for handler in config['handlers'].values():
            if 'filename' in handler:
                handler['filename'] = os.path.join(logs_dir, os.path.basename(handler['filename']))
        
        logging.config.dictConfig(config)

        self.err_logger = logging.getLogger("main")
        sys.excepthook = self.handle_exception

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        self.err_logger.error("Unexpected exception",
                              exc_info=(exc_type, exc_value, exc_traceback))
