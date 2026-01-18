"""
Telegram 消息处理器 - 高性能异步版
修复点：Markdown 符号转义、并发任务限制、超时逻辑优化、发送重试机制、编辑消息避免 'Message is not modified' 错误
"""
import re
import asyncio
import httpx
from io import BytesIO
from typing import Dict

from telegram.ext import ContextTypes
from telegram import Update, InputMediaPhoto
from telegram.constants import ChatType, ParseMode
from telegram.error import TimedOut, NetworkError, BadRequest
from telegram.helpers import escape_markdown

from videos.adapter.adapter_base import ShortVideoInfoResponse
from videos.video_adapter import get_short_video_adapter
from internal.logger.logger import logger

# 异步客户端配置：复用连接池
async_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, read=60.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    follow_redirects=True,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)

# 用户任务锁
current_limiting_lock_map: Dict[int, bool] = {}

# URL 匹配正则
URL_PATTERN = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'

async def retry_send(send_func, *args, retries=3, delay=2, **kwargs):
    """重试发送函数，用于处理超时异常，并忽略 'Message is not modified' BadRequest"""
    for attempt in range(retries):
        try:
            return await send_func(*args, **kwargs)
        except TimedOut:
            if attempt < retries - 1:
                logger.warning(f"发送超时，重试 {attempt + 1}/{retries}")
                await asyncio.sleep(delay)
            else:
                raise
        except BadRequest as e:
            if "Message is not modified" in str(e):
                logger.debug(f"忽略编辑消息未修改错误: {e}")
                return None  # 忽略并返回 None，表示操作成功（无需进一步处理）
            else:
                raise  # 其他 BadRequest 重新抛出

async def on_text_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息主入口"""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    text = update.message.text
    is_group = update.message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]

    # 命令过滤
    if text.startswith("/start"):
        await retry_send(update.message.reply_text, "👋 发送短视频链接，我来为你解析无水印版本。")
        return

    # 提取链接
    urls = re.findall(URL_PATTERN, text)
    if not urls:
        if not is_group:
            await retry_send(update.message.reply_text, "❌ 请发送有效的视频链接")
        return

    # 并发锁
    if user_id in current_limiting_lock_map:
        await retry_send(update.message.reply_text, "⏰ 任务正在处理中，请稍后...")
        return

    short_video_uri = urls[0]
    video_adapter = get_short_video_adapter(short_video_uri)

    if not video_adapter:
        if not is_group:
            await retry_send(update.message.reply_text, "❌ 暂不支持该平台")
        return

    current_limiting_lock_map[user_id] = True
    try:
        status_msg = await retry_send(update.message.reply_text, "🎬 正在解析，请稍候...")
    except TimedOut as e:
        logger.error(f"发送状态消息超时: {e}")
        status_msg = None  # 如果失败，继续解析但无状态消息

    try:
        # 在线程池中执行同步解析逻辑
        loop = asyncio.get_running_loop()
        video_info: ShortVideoInfoResponse = await loop.run_in_executor(
            None, video_adapter.get_short_video_info, short_video_uri
        )

        if not video_info or not video_info.no_watermark_download_url:
            raise ValueError("解析地址获取为空")

        if status_msg:
            await retry_send(status_msg.delete)

        # 分流：图集 vs 视频
        if '\n' in video_info.no_watermark_download_url:
            await handle_image_album_async(update, video_info)
        else:
            await handle_video_async(update, video_info)

    except Exception as e:
        logger.error(f"解析失败: {e} | URL: {short_video_uri}")
        try:
            await retry_send(update.message.reply_text, "😭 解析失败，链接可能已失效或受到平台限制")
        except: pass
    finally:
        current_limiting_lock_map.pop(user_id, None)

async def handle_video_async(update: Update, video_info: ShortVideoInfoResponse):
    """发送视频：直接使用 Markdown 链接，无需下载或直传"""
    video_url = video_info.no_watermark_download_url
    title = escape_markdown(video_info.title or "短视频解析", version=2)

    text = f"🎬 *{title}*\n\n🔗 [点击跳转播放视频]({video_url})"
    try:
        await retry_send(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=False)
    except BadRequest as e:
        logger.warning(f"Markdown 发送失败，尝试纯文本: {e}")
        # 兜底纯文本
        raw_text = f"🎬 {video_info.title or '短视频解析'}\n\n点击跳转播放视频: {video_url}"
        await retry_send(update.message.reply_text, raw_text)

async def handle_image_album_async(update: Update, video_info: ShortVideoInfoResponse):
    """高性能图集：并发下载 -> 分批发货（每批 10 张，处理多图场景，并提供进度提示）"""
    image_urls = [u.strip() for u in video_info.no_watermark_download_url.split('\n') if u.strip()]
    total_images = len(image_urls)
    if total_images == 0:
        logger.warning("无有效图片 URL")
        return

    batch_size = 10
    total_batches = (total_images + batch_size - 1) // batch_size

    # 如果多批，创建进度消息
    progress_msg = None
    last_progress_text = None  # 追踪上次文本，避免重复编辑
    if total_batches > 1:
        initial_text = f"🖼️ 检测到 {total_images} 张图片，将分 {total_batches} 批发送...\n进度: 0/{total_batches} 批 (剩余 {total_images} 张，剩余 {total_batches} 批)"
        try:
            progress_msg = await retry_send(update.message.reply_text, initial_text)
            last_progress_text = initial_text
        except TimedOut as e:
            logger.error(f"发送进度消息超时: {e}")
            progress_msg = None

    current_batch = 0
    sent_images = 0

    for i in range(0, total_images, batch_size):
        current_batch += 1
        batch_urls = image_urls[i:i + batch_size]

        # 并发下载当前批次
        tasks = [async_client.get(url) for url in batch_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        media_group = []
        for idx, resp in enumerate(results):
            if isinstance(resp, Exception):
                logger.warning(f"图片下载失败 (URL: {batch_urls[idx]}): {resp}")
                continue

            if isinstance(resp, httpx.Response) and resp.status_code == 200:
                img_stream = BytesIO(resp.content)
                cap = format_caption(video_info) if (i == 0 and idx == 0) else None
                media_group.append(InputMediaPhoto(media=img_stream, caption=cap))

        if media_group:
            try:
                await retry_send(update.message.reply_media_group, media=media_group, read_timeout=60)
                sent_images += len(media_group)
            except (TimedOut, NetworkError):
                logger.warning("图集发送超时，任务可能仍在排队")
            except BadRequest as e:
                logger.error(f"媒体组发送失败: {e}")
                # 兜底：逐张发送当前批次
                for media in media_group:
                    try:
                        await retry_send(update.message.reply_photo, photo=media.media, caption=media.caption)
                        sent_images += 1
                    except Exception as inner_e:
                        logger.error(f"单张发送失败: {inner_e}")
            except Exception as e:
                logger.error(f"图集发送失败: {e}")

        # 更新进度（如果有）
        if progress_msg:
            remaining_batches = total_batches - current_batch
            remaining_images = max(total_images - sent_images, 0)  # 避免负数
            new_text = (
                f"🖼️ 检测到 {total_images} 张图片，将分 {total_batches} 批发送...\n"
                f"进度: {current_batch}/{total_batches} 批 (剩余 {remaining_images} 张，剩余 {remaining_batches} 批)"
            )
            if new_text != last_progress_text:  # 仅在内容变化时编辑
                try:
                    await retry_send(progress_msg.edit_text, new_text)
                    last_progress_text = new_text
                except TimedOut as e:
                    logger.error(f"编辑进度消息超时: {e}")
            else:
                logger.debug("进度文本未变化，跳过编辑")

    # 完成后，编辑为完成消息
    if progress_msg:
        complete_text = "🖼️ 图集发送完成！"
        if complete_text != last_progress_text:
            try:
                await retry_send(progress_msg.edit_text, complete_text)
            except TimedOut as e:
                logger.error(f"编辑完成消息超时: {e}")
        else:
            logger.debug("完成文本未变化，跳过编辑")


async def send_cover_fallback(update: Update, video_info: ShortVideoInfoResponse, reason: str):
    """兜底方案：发送封面 + 直链（增强 Markdown 转义，确保无报错）"""
    clean_title = escape_markdown(video_info.title or "解析结果", version=2)
    clean_reason = escape_markdown(reason, version=2)
    clean_url = video_info.no_watermark_download_url

    text = (
        f"✅ *解析完成*\n"
        f"📝 {clean_title}\n\n"
        f"🔗 [点击跳转下载视频]({clean_url})\n\n"
        f"💡 提示: {clean_reason}"
    )

    try:
        if video_info.cover:
            await retry_send(update.message.reply_photo, photo=video_info.cover, caption=text, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await retry_send(update.message.reply_text, text, parse_mode=ParseMode.MARKDOWN_V2, disable_web_page_preview=False)
    except BadRequest as e:
        logger.warning(f"Markdown 发送失败，尝试纯文本: {e}")
        raw_text = (
            f"✅ 解析完成\n"
            f"📝 {video_info.title or '解析结果'}\n\n"
            f"🔗 点击跳转下载视频: {clean_url}\n\n"
            f"💡 提示: {reason}"
        )
        await retry_send(update.message.reply_text, raw_text)


def format_caption(video_info: ShortVideoInfoResponse) -> str:
    """格式化标题"""
    title = video_info.title or "短视频解析"
    author = f"\n👤 作者: {video_info.author_name}" if video_info.author_name else ""
    return f"📝 {title}{author}"[:1000]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    await retry_send(update.message.reply_text,
                     "👋 欢迎使用短视频无水印解析机器人！\n\n"
                     "📱 *私聊使用*：直接发送视频链接\n"
                     "👥 *群组使用*：发送链接即可解析",
                     parse_mode=ParseMode.MARKDOWN)