"""视频适配器基类和响应模型"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ShortVideoInfoResponse:
    """短视频信息响应"""
    author_name: str = ""
    author_avatar: str = ""
    title: str = ""
    cover: str = ""
    created_at: str = ""
    no_watermark_download_url: str = ""


class IVideosInterface(ABC):
    """视频适配器接口"""

    @abstractmethod
    def get_short_video_info(self, url: str) -> Optional[ShortVideoInfoResponse]:
        """获取短视频信息"""
        pass