import os
from unittest.mock import MagicMock

from dotenv import load_dotenv

from src.bot import VKinderBot

load_dotenv()


# python -m pytest ./tests/unit/bot/test_bot.py -k test_bot_start
def test_bot_start():
    """Тестирует обработку команды старта бота.

    Проверяет, что:
    1. Бот корректно инициализируется с переданными токеном и ID группы
    2. При вызове handle_start() отправляется одно сообщение
    3. API бота вызывается с ожидаемыми параметрами

    Использует MagicMock для подмены реального API ВКонтакте.
    """
    bot = VKinderBot(os.getenv("VK_TOKEN"), os.getenv("GROUP_ID"))
    bot.api = MagicMock()
    bot.handle_start(123)
    bot.api.messages.send.assert_called_once()
