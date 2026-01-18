"""配置模块"""
from .config import (
    GlobalConfig,
    get_global_instance,
    get_log_instance,
    get_telegram_instance,
    get_app_version
)

__all__ = [
    'GlobalConfig',
    'get_global_instance',
    'get_log_instance',
    'get_telegram_instance',
    'get_app_version'
]