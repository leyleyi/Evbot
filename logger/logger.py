# Logger
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from internal.config import get_global_instance, get_log_instance
class Logger:
    _instance = None
    def __init__(self):
        config = get_global_instance()
        log_config = get_log_instance()
        log_path = os.path.join(config.app_path, 'log')
        os.makedirs(log_path, exist_ok=True)
        log_file = os.path.join(log_path, "evbot.log")
        self.logger = logging.getLogger('Evbot')
        self.logger.setLevel(logging.DEBUG)

        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=log_config.max_backups,
            encoding='utf-8'
        )
        file_handler.rotator = self._date_rotator
        file_handler.namer = self._date_namer

        console_handler = logging.StreamHandler()

        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d - %(process)d - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    @staticmethod
    def _date_rotator(source, dest):
        """自定义 rotator：在轮转时不立即重命名，让 namer 处理"""
        pass  # 默认行为即可，namer 会处理命名

    @staticmethod
    def _date_namer(default_name):
        """自定义 namer：为备份文件添加日期后缀，如 evbot.20260118.log"""
        base_filename, ext, suffix = default_name.rsplit('.', 2)
        date_str = datetime.now().strftime('%Y%m%d')  # 使用当前日期
        return f"{base_filename}_{date_str}.{ext}"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = Logger()
        return cls._instance.logger

    def log_received_url(self, url: str, context: str = ""):
        message = f"Received URL: {url}"
        if context:
            message += f" (Context: {context})"
        self.logger.info(message)
        print(f"[CONSOLE] {message}")


# 导出全局 logger
logger = Logger.get_instance()