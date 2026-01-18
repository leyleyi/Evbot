"""抖音视频适配器"""
import re
import json
from typing import Optional
from videos.adapter.adapter_base import IVideosInterface, ShortVideoInfoResponse
from internal.http_client.client import HttpClient
from internal.logger.logger import logger


class DouyinAdapter(IVideosInterface):
    """抖音适配器"""

    def get_short_video_info(self, url: str) -> Optional[ShortVideoInfoResponse]:
        try:
            # 第一步：获取重定向后的 URL 提取视频 ID
            session = HttpClient.get_http_client()
            header_resp = session.head(url, allow_redirects=True)

            redirect_url = header_resp.url

            # 提取视频 ID
            video_id = self._extract_video_id(redirect_url)
            if not video_id:
                raise Exception("无法提取视频 ID")

            # 第二步：访问分享页面获取完整数据
            share_url = f"https://www.iesdouyin.com/share/video/{video_id}"
            mobile_session = HttpClient.get_mobile_request()
            get_resp = mobile_session.get(share_url)

            # 第三步：从 HTML 中提取 JSON 数据
            html_content = get_resp.text
            pattern = r'window\._ROUTER_DATA\s*=\s*(.*?)</script>'
            match = re.search(pattern, html_content)

            if not match:
                raise Exception("无法从页面中提取数据")

            # 解析 JSON
            router_data = json.loads(match.group(1))

            # 获取视频数据
            item_list = router_data.get('loaderData', {}).get('video_(id)/page', {}).get('videoInfoRes', {}).get(
                'item_list', [])

            if not item_list:
                raise Exception("未找到视频数据")

            data = item_list[0]
            title = data.get('desc', '')

            # 判断是视频还是图集
            aweme_type = data.get('aweme_type', 0)

            if aweme_type != 2:
                # 视频类型
                video = data.get('video')
                if not video or not video.get('play_addr', {}).get('url_list'):
                    raise Exception("视频数据不完整")

                # 获取无水印视频链接并切换分辨率
                video_url = video['play_addr']['url_list'][0]
                video_url = video_url.replace('playwm', 'play').replace('720p', '0')

                cover_url = ""
                if video.get('cover', {}).get('url_list'):
                    cover_url = video['cover']['url_list'][0]

                return ShortVideoInfoResponse(
                    author_name=data.get('author', {}).get('nickname', ''),
                    author_avatar=self._get_author_avatar(data),
                    title=title,
                    cover=cover_url,
                    created_at="",
                    no_watermark_download_url=video_url
                )
            else:
                # 图集类型
                images = data.get('images', [])
                if not images:
                    raise Exception("图集数据不完整")

                # 获取所有图片 URL（使用第4个 URL，索引为3）
                image_urls = []
                for img in images:
                    url_list = img.get('url_list', [])
                    if len(url_list) > 3:
                        image_urls.append(url_list[3])
                    elif url_list:
                        image_urls.append(url_list[0])

                # 将所有图片 URL 用换行符连接成一个字符串
                all_images_url = '\n'.join(image_urls)

                return ShortVideoInfoResponse(
                    author_name=data.get('author', {}).get('nickname', ''),
                    author_avatar=self._get_author_avatar(data),
                    title=title,
                    cover=image_urls[0] if image_urls else "",
                    created_at="",
                    no_watermark_download_url=all_images_url
                )

        except Exception as e:
            logger.error(f"抖音解析失败: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """提取视频 ID"""
        patterns = [
            r'/video/(\d+)',
            r'/(\d+)\?',
            r'/(\d+)$',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # 如果上述模式都不匹配，尝试从路径中获取最后一段数字
        parts = url.rstrip('/').split('/')
        for part in reversed(parts):
            if re.match(r'^\d+$', part):
                return part

        return None

    def _get_author_avatar(self, data: dict) -> str:
        """获取作者头像"""
        avatar_list = data.get('author', {}).get('avatar_larger', {}).get('url_list', [])
        return avatar_list[0] if avatar_list else ""