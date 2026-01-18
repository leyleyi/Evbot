# Telegram Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from internal.config.config import get_telegram_instance
from internal.logger.logger import logger
from telegram_bot.handler import on_text_handle, start_command


class TelegramBot:
    def __init__(self):
        self.telegram_config = get_telegram_instance()
        self.application = None

    def start(self):
        try:
            self.application = Application.builder().token(
                self.telegram_config.api_token
            ).build()
            self._register_handlers()
            logger.info("Evbot 启动成功，开始监听消息...")
            self.application.run_polling(allowed_updates=['message'])
        except Exception as e:
            logger.error(f"启动失败: {e}")
            raise

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_handle)
        )
