"""快手视频适配器"""
import re
import json
from typing import Optional, Dict, Any
from videos.adapter.adapter_base import IVideosInterface, ShortVideoInfoResponse
from internal.http_client.client import HttpClient
from internal.logger.logger import logger


class KuaishouAdapter(IVideosInterface):
    """快手适配器"""

    def get_short_video_info(self, url: str) -> Optional[ShortVideoInfoResponse]:
        try:
            # 第一步：获取重定向后的真实地址
            session = HttpClient.get_http_client()
            header_resp = session.get(url, allow_redirects=True)
            redirect_url = header_resp.url
            logger.info(f"快手重定向URL: {redirect_url}")

            # 第二步：获取页面内容
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            get_resp = session.get(redirect_url)
            html_content = get_resp.text

            # 第三步：尝试匹配视频数据
            video_pattern = r'window\.__APOLLO_STATE__\s*=\s*(\{.*?\})\s*;\(function\(\)\{'
            video_match = re.search(video_pattern, html_content)

            if video_match:
                # 视频类型
                logger.info("检测到快手视频类型")
                return self._parse_kuaishou_video(redirect_url, video_match.group(1))

            # 第四步：尝试匹配图集数据
            atlas_pattern = r'window\.INIT_STATE\s*=\s*({.*?})(?:\s*;|\s*</script>)'
            atlas_match = re.search(atlas_pattern, html_content)

            if atlas_match:
                # 图集类型
                logger.info("检测到快手图集类型")
                return self._parse_kuaishou_atlas(atlas_match.group(1))

            raise Exception("未能匹配到快手数据")

        except Exception as e:
            logger.error(f"快手解析失败: {e}")
            return None

    def _parse_kuaishou_video(self, redirect_url: str, json_data: str) -> Optional[ShortVideoInfoResponse]:
        """解析视频类型"""
        # 提取视频ID
        video_id_pattern = r'/short-video/([a-zA-Z0-9]+)'
        video_id_match = re.search(video_id_pattern, redirect_url)

        if not video_id_match:
            raise Exception("无法提取视频ID")

        video_id = video_id_match.group(1)
        logger.info(f"视频ID: {video_id}")

        # 解析JSON数据
        apollo_state = json.loads(json_data)

        # 获取 defaultClient
        default_client = apollo_state.get('defaultClient')
        if not default_client:
            raise Exception("defaultClient不存在")

        # 获取视频详情
        video_key = f"VisionVideoDetailPhoto:{video_id}"
        video_info_raw = default_client.get(video_key)
        if not video_info_raw:
            raise Exception(f"未找到视频信息: {video_key}")

        caption = video_info_raw.get('caption', '')
        photo_url = video_info_raw.get('photoUrl', '')
        cover_url = video_info_raw.get('coverUrl', '')

        return ShortVideoInfoResponse(
            author_name="",
            author_avatar="",
            title=caption,
            cover=cover_url,
            created_at="",
            no_watermark_download_url=photo_url
        )

    def _parse_kuaishou_atlas(self, json_data: str) -> Optional[ShortVideoInfoResponse]:
        """解析图集类型"""
        # 提取图集信息
        atlas_info = self._extract_atlas_info(json_data)
        if not atlas_info:
            raise Exception("未能解析图集信息")

        atlas_list = atlas_info.get('ext_params', {}).get('atlas', {}).get('list', [])
        atlas_cdn = atlas_info.get('ext_params', {}).get('atlas', {}).get('cdn', [])

        if not atlas_list:
            raise Exception("图集列表为空")

        if not atlas_cdn:
            raise Exception("图集CDN为空")

        image_cdn = atlas_cdn[0]
        image_urls = []

        # 拼接图片URL
        for image_path in atlas_list:
            # 将 webp 转为 jpg
            image_path = image_path.replace('webp', 'jpg')
            image_url = f"https://{image_cdn}{image_path}"
            image_urls.append(image_url)

        # 用换行符连接所有图片URL
        all_images_url = '\n'.join(image_urls)

        return ShortVideoInfoResponse(
            author_name="",
            author_avatar="",
            title=atlas_info.get('caption', ''),
            cover=image_urls[0] if image_urls else "",
            created_at="",
            no_watermark_download_url=all_images_url
        )

    def _extract_atlas_info(self, json_text: str) -> Optional[Dict[str, Any]]:
        """提取图集信息"""
        # 查找 "photo" : { 的模式
        pattern = r'"photo"\s*:\s*\{'
        matches = list(re.finditer(pattern, json_text))

        if not matches:
            raise Exception("未找到photo字段")

        # 提取完整的photo对象
        for match in matches:
            start = match.end() - 1  # 从 { 开始
            brace_count = 1
            index = start + 1

            while index < len(json_text):
                if json_text[index] == '{':
                    brace_count += 1
                elif json_text[index] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = index + 1
                        photo_json = json_text[start:end]

                        # 尝试解析
                        try:
                            atlas_info = json.loads(photo_json)
                            if atlas_info.get('ext_params', {}).get('atlas', {}).get('list'):
                                return atlas_info
                        except:
                            pass
                        break
                index += 1

        raise Exception("未能解析图集信息")