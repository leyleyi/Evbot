"""日志模块"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from internal.config import get_global_instance, get_log_instance


class Logger:
    _instance = None
    def __init__(self):
        config = get_global_instance()
        log_config = get_log_instance()

        log_path = os.path.join(config.app_path, 'log')
        os.makedirs(log_path, exist_ok=True)
        log_file = os.path.join(
            log_path,
            f"log_{datetime.now().strftime('%Y%m%d')}.log"
        )

        self.logger = logging.getLogger('Evbot')
        self.logger.setLevel(logging.DEBUG)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.max_size * 1024 * 1024,
            backupCount=log_config.max_backups,
            encoding='utf-8'
        )

        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance.logger

logger = Logger.get_instance()