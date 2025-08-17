import os
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.bot import VKinderBot
from src.db.vkinder_models import Base


@pytest.fixture(scope='session')
def db_engine():
    """Фикстура для создания тестовой базы данных в памяти.

    Returns:
        Engine: SQLAlchemy engine для временной SQLite базы данных.
        Создает все таблицы перед тестами и удаляет их после завершения.
    """
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(db_engine):
    """Фикстура для создания изолированной сессии БД с откатом изменений.

    Args:
        db_engine: Фикстура с тестовым движком БД

    Yields:
        Session: Новая сессия SQLAlchemy для тестов

    Особенности:
        - Все изменения откатываются после теста
        - Каждый тест получает чистую сессию
        - Автоматически закрывает соединение
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def mock_user_data():
    """Фикстура с тестовыми данными пользователя VK.

    Returns:
        dict: Словарь с mock-данными профиля пользователя:
        - id: 1
        - Имя/фамилия
        - Пол
        - Город
        - Дата рождения
        - URL профиля
    """
    return {
        'id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'sex': 2,
        'city': {'title': 'Moscow'},
        'bdate': '01.01.1990',
        'domain': 'testuser'
    }


@pytest.fixture
def api_handler():
    """Фикстура для создания тестового обработчика VK API.

    Returns:
        VKAPIHandler: Экземпляр обработчика с мокированным:
        - API клиентом VK
        - Базовыми методами API
    """
    with patch('vk_api.VkApi'):
        from src.vk_api_handler import VKAPIHandler
        handler = VKAPIHandler("test_token", 123)
        handler.api = MagicMock()
        return handler


@pytest.fixture
def bot():
    """Фикстура для создания тестового экземпляра бота.

    Returns:
        VKinderBot: Экземпляр бота с мокированными:
        - API VK (messages)
        - Обработчиком VK API
        - Сессией БД

    Особенности:
        - Использует spec для проверки интерфейса
        - Сохраняет оригинальную функциональность
        - Изолирует тесты от реальных вызовов API
    """
    # Создаем полностью изолированный тестовый бот
    bot = MagicMock(spec=VKinderBot)  # Используем spec для проверки интерфейса

    # Настраиваем необходимые атрибуты
    bot.api = MagicMock()
    bot.api.messages = MagicMock()
    bot.api.messages.send = MagicMock()

    bot.vk_handler = MagicMock()
    bot.db_session = MagicMock()

    bot.current_candidates = {}

    # Возвращаем и оригинальный бот, и мок
    real_bot = VKinderBot(os.getenv("VK_TOKEN"), os.getenv("GROUP_ID"))
    real_bot.api = bot.api
    real_bot.vk_handler = bot.vk_handler
    real_bot.db_session = bot.db_session

    return real_bot