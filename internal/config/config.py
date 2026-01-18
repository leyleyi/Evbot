"""配置管理模块"""
import os
import toml
from typing import Optional


class CookieConfig:
    def __init__(self, config_dict: dict):
        self.kuaishou_cookie = config_dict.get('kuaishou_cookie', '')
        self.xigua_cookie = config_dict.get('xigua_cookie', '')


class LogConfig:
    def __init__(self, config_dict: dict):
        self.max_size = config_dict.get('max_size', 32)
        self.max_age = config_dict.get('max_age', 7)
        self.max_backups = config_dict.get('max_backups', 3)


class TelegramConfig:
    def __init__(self, config_dict: dict):
        self.api_token = config_dict.get('api_token', '')


class GlobalConfig:
    _instance: Optional['GlobalConfig'] = None

    def __init__(self):
        self.app_path = os.getcwd()
        config_path = os.path.join(self.app_path, 'config.toml')

        try:
            config = toml.load(config_path)
        except Exception as e:
            raise Exception(f"加载配置文件失败: {e}")

        self.cookie_config = CookieConfig(config.get('cookie', {}))
        self.log_config = LogConfig(config.get('log', {}))
        self.telegram_config = TelegramConfig(config.get('telegram', {}))
        self.app_version = "v1.0"

    @classmethod
    def get_instance(cls) -> 'GlobalConfig':
        if cls._instance is None:
            cls._instance = GlobalConfig()
        return cls._instance


def get_global_instance() -> GlobalConfig:
    return GlobalConfig.get_instance()


def get_log_instance() -> LogConfig:
    return GlobalConfig.get_instance().log_config


def get_telegram_instance() -> TelegramConfig:
    return GlobalConfig.get_instance().telegram_config


def get_app_version() -> str:
    return GlobalConfig.get_instance().app_version