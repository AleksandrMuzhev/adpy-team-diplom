import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import vk_api

from src.bot import VKinderBot, logger
from src.vk_api_handler import VKAPIHandler

load_dotenv()

def check_token(token: str) -> bool:
    """
    Проверяет валидность токена VK API.

    Args:
        token (str): Токен для проверки.

    Returns:
        bool: True если токен валиден, False при ошибке.

    Logs:
        Ошибки проверки токена.
    """
    try:
        vk_api.VkApi(token=token).get_api().groups.getById()
        return True
    except Exception as e:
        logger.error(f"Token check failed: {e}")
        return False


def main():
    """
    Основная точка входа для запуска бота VKinder.

    Процесс:
        1. Установка рабочей директории скрипта.
        2. Получение токена группы, пользовательского токена и ID группы из окружения.
        3. Проверка валидности токена группы.
        4. Инициализация обработчика VK API (VKAPIHandler).
        5. Создание объекта бота VKinderBot и запуск цикла бота.

    Raises:
        ValueError: При отсутствии VK_TOKEN или GROUP_ID в окружении.
    """
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    group_token = os.getenv("VK_TOKEN")
    user_token = os.getenv("USER_TOKEN")
    group_id_str = os.getenv("GROUP_ID")

    if not group_token or not group_id_str:
        raise ValueError("Необходимо указать VK_TOKEN и GROUP_ID в .env файле")

    if not check_token(group_token):
        logger.error("Invalid VK_TOKEN")
        return

    group_id = int(group_id_str)

    vk_handler = VKAPIHandler(group_token=group_token, group_id=group_id, user_token=user_token)

    bot = VKinderBot(vk_handler, group_id)
    bot.run()


if __name__ == "__main__":
    """
    Обрабатывает аргументы командной строки:
        --test - запускает тесты через pytest.
        Иначе - запускает функцию main.
    """
    if "--test" in sys.argv:
        import pytest
        pytest.main(["-v", "tests/"])
    else:
        main()
