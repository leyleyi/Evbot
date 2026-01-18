"""视频适配器工厂"""
from typing import Optional
from videos.adapter.adapter_base import IVideosInterface
from videos.adapter.douyin_adapter import DouyinAdapter
from videos.adapter.kuaishou_adapter import KuaishouAdapter


def get_short_video_adapter(url: str) -> Optional[IVideosInterface]:
    """根据 URL 获取对应的视频适配器"""
    if 'douyin' in url:
        return DouyinAdapter()
    if 'kuaishou' in url:
        return KuaishouAdapter()
    return None