"""视频适配器包"""
from .adapter_base import IVideosInterface, ShortVideoInfoResponse
from .douyin_adapter import DouyinAdapter
from .kuaishou_adapter import KuaishouAdapter

__all__ = [
    'IVideosInterface',
    'ShortVideoInfoResponse',
    'DouyinAdapter',
    'KuaishouAdapter'
]

