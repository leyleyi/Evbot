"""主程序入口"""
from telegram_bot.bot import TelegramBot
from internal.config.config import get_app_version
from internal.logger.logger import logger


def print_banner():
    banner = """
  ______           _               _   
 |  ____|         | |             | |  
 | |__    __   __ | |__     ___   | |_ 
 |  __|   \\ \\ / / | '_ \\   / _ \\  | __|
 | |____   \\ V /  | |_) | | (_) | | |_ 
 |______|   \\_/   |_.__/   \\___/   \\__|
    """
    print("Evbot Start...")
    print(banner)
    print(f"Evbot version({get_app_version()}) Powered by Leyi\n")


def main():
    print_banner()
    bot = TelegramBot()
    bot.start()


if __name__ == "__main__":
    main()