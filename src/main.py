import os
import sys

from dotenv import load_dotenv
from vk_api import vk_api

from src.bot import VKinderBot, logger

load_dotenv()


def check_token(token):
    """
    Проверяет валидность токена VK API.

    Args:
        token (str): Токен для проверки

    Returns:
        bool: True если токен валиден, False в случае ошибки

    Note:
        Логирует ошибки проверки токена
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

    Workflow:
        1. Устанавливает рабочую директорию
        2. Проверяет валидность токена
        3. Получает настройки из переменных окружения
        4. Создает и запускает экземпляр бота

    Raises:
        ValueError: Если отсутствуют обязательные переменные окружения
        VkApiError: При проблемах с API ВКонтакте

    Environment Variables:
        VK_TOKEN: Токен группы VK
        GROUP_ID: ID группы бота

    Note:
        Для корректной работы необходимо предварительно:
        - Создать файл .env с настройками
        - Установить зависимости из requirements.txt
    """
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    if not check_token(os.getenv("VK_TOKEN")):
        logger.error("Invalid VK_TOKEN")
        return
    group_token = os.getenv("VK_TOKEN")
    group_id = int(os.getenv("GROUP_ID"))

    if not group_token or not group_id:
        raise ValueError("Необходимо указать VK_TOKEN и GROUP_ID в .env файле")

    bot = VKinderBot(group_token, group_id)
    bot.run()


if __name__ == "__main__":
    if "--test" in sys.argv:
        # Запуск тестов через pytest
        import pytest

        pytest.main(["-v", "tests/"])
    else:
        main()
