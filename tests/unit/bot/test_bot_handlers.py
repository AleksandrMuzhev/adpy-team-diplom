import os
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

from src.bot import VKinderBot

load_dotenv()


@pytest.fixture
def bot():
    """Фикстура для создания тестового экземпляра бота с мокированными зависимостями.

    Returns:
        VKinderBot: Экземпляр бота с подмененными:
        - vk_handler (обработчик VK API)
        - db (модуль работы с БД)
        - vk (основной API ВКонтакте)
    """
    bot = VKinderBot(os.getenv("VK_TOKEN"), os.getenv("GROUP_ID"))

    # Мокируем все зависимости
    bot.vk_handler = MagicMock()
    bot.vk_handler.send_message = MagicMock()  # Добавляем мок для send_message

    bot.db = MagicMock()
    bot.db.add_favorite = MagicMock()
    bot.db.get_favorites_for_user = MagicMock(return_value=[])

    bot.current_candidates = {}

    # Мокируем VK API
    bot.vk = MagicMock()
    bot.vk.messages = MagicMock()
    bot.vk.messages.send = MagicMock(return_value=True)

    return bot


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_send_message
def test_send_message(bot):
    """Тестирует базовую отправку сообщения через VK API.

    Проверяет что:
    - Сообщение отправляется с правильными параметрами
    - Генерируется случайный ID сообщения
    - Необязательные параметры (клавиатура, вложения) не передаются
    """
    with patch.object(bot, 'api') as mock_api:
        mock_api.messages.send.return_value = True

        # Вызываем тестируемый метод
        bot.send_message(123, "Test message")

        # Проверяем вызов API
        mock_api.messages.send.assert_called_once()

        # Получаем аргументы вызова
        call_args = mock_api.messages.send.call_args[1]

        # Проверяем основные параметры
        assert call_args['user_id'] == 123
        assert call_args['message'] == "Test message"
        assert isinstance(call_args['random_id'], int)  # random_id генерируется

        # Проверяем отсутствие необязательных параметров
        assert 'keyboard' not in call_args
        assert 'attachment' not in call_args


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_send_message_with_attachments
def test_send_message_with_attachments(bot):
    """Тестирует отправку сообщения с дополнительными параметрами.

    Проверяет корректную передачу:
    - Клавиатуры (через метод get_keyboard())
    - Вложений (в виде строки attachment)
    - Всех обязательных параметров сообщения
    """
    with patch.object(bot, 'api') as mock_api:
        mock_api.messages.send.return_value = True

        # Создаем мок клавиатуры
        mock_keyboard = MagicMock()
        mock_keyboard.get_keyboard.return_value = {"buttons": []}

        # Вызываем метод с доп. параметрами
        bot.send_message(
            user_id=123,
            message="Test with attachments",
            keyboard=mock_keyboard,
            attachments="photo123_456"
        )

        # Проверяем вызов
        mock_api.messages.send.assert_called_once()
        call_args = mock_api.messages.send.call_args[1]

        assert call_args['user_id'] == 123
        assert call_args['message'] == "Test with attachments"
        assert call_args['keyboard'] == {"buttons": []}
        assert call_args['attachment'] == "photo123_456"


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_start
def test_handle_start(bot):
    """Тестирует обработку команды старта (/start).

    Проверяет что:
    - Отправляется ровно одно сообщение
    - Сообщение содержит приветственный текст
    - Вызывается основной метод send_message
    """
    with patch.object(bot, 'send_message') as mock_send:
        bot.handle_start(123)
        mock_send.assert_called_once()
        assert "привет" in mock_send.call_args[0][1].lower()


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_find_pair
def test_handle_find_pair(bot):
    """Тестирует функционал поиска потенциальных пар.

    Проверяет что:
    - Вызывается метод поиска совпадений
    - Найденные кандидаты сохраняются в current_candidates
    - Для поиска используются данные пользователя
    """
    mock_candidate = MagicMock(
        id=456,
        first_name="Test",
        last_name="User",
        age=25,
        city="Moscow",
        profile_url="https://vk.com/id456"
    )
    bot.vk_handler.find_potential_matches.return_value = [mock_candidate]

    bot.handle_find_pair(123)
    assert 123 in bot.current_candidates


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_help
def test_handle_help(bot):
    """Тестирует отображение справки (/help).

    Проверяет что:
    - Отправляется ровно одно сообщение
    - Сообщение содержит текст помощи
    - Вызывается основной метод send_message
    """
    with patch.object(bot, 'send_message') as mock_send:
        bot.handle_help(123)
        mock_send.assert_called_once()
        assert "помощь" in mock_send.call_args[0][1].lower()


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_add_to_favorites
def test_handle_add_to_favorites(bot):
    """Тестирует добавление кандидата в избранное.

    Проверяет что:
    - Вызывается метод добавления в БД
    - Отправляется подтверждающее сообщение
    - Используется правильная клавиатура
    - Обрабатывается текущий кандидат из списка
    """
    mock_candidate = MagicMock(
        id=456,
        first_name="Test",
        last_name="User",
        age=25,
        city="Moscow",
        profile_url="https://vk.com/id456"
    )

    # Настраиваем текущие кандидаты и индекс
    bot.current_candidates = {123: [mock_candidate]}
    bot.current_index = {123: 0}

    # Мокируем методы, которые должны вызываться
    with patch.object(bot, 'send_message') as mock_send_message, \
            patch('src.bot.Session') as mock_session, \
            patch('src.bot.add_favorite') as mock_add_favorite, \
            patch.object(bot, 'create_candidate_keyboard') as mock_create_keyboard:
        # Настраиваем мок для сессии
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

        # Настраиваем возвращаемое значение для create_candidate_keyboard
        mock_keyboard = MagicMock()
        mock_create_keyboard.return_value = mock_keyboard

        # Вызываем метод
        bot.handle_add_to_favorites(123)

        # Проверяем, был ли вызван метод добавления в избранное
        mock_add_favorite.assert_called_once()
        # Проверяем, что send_message был вызван с правильным сообщением и клавиатурой
        mock_send_message.assert_called_once_with(
            123,
            f"Добавлено в избранное: {mock_candidate.first_name} {mock_candidate.last_name}",
            mock_keyboard  # Используем мок клавиатуры
        )


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_show_favorites
def test_handle_show_favorites(bot):
    """Тестирует отображение списка избранных кандидатов.

    Проверяет что:
    - Запрашиваются данные из БД
    - Отправляется сообщение со списком
    - Сообщение содержит данные кандидатов
    """
    mock_favorite = MagicMock(
        id=789,
        first_name="Favorite",
        last_name="User"
    )
    bot.db.get_favorites_for_user.return_value = [mock_favorite]

    with patch.object(bot, 'send_message') as mock_send:
        bot.handle_show_favorites(123)
        mock_send.assert_called_once()


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_show_empty_favorites
def test_handle_show_empty_favorites(bot):
    """Тестирует отображение пустого списка избранного.

    Проверяет что:
    - При отсутствии избранных отправляется сообщение
    - Сообщение содержит информацию об отсутствии кандидатов
    - Не возникает ошибок при пустом списке
    """
    bot.db.get_favorites_for_user.return_value = []

    with patch.object(bot, 'send_message') as mock_send:
        bot.handle_show_favorites(123)
        mock_send.assert_called_once()
        assert "нет избранных" in mock_send.call_args[0][1].lower()


# python -m pytest ./tests/unit/bot/test_bot_handlers.py -k test_handle_find_pair_no_matches
def test_handle_find_pair_no_matches(bot):
    """Тестирует обработку случая, когда не найдено кандидатов.

    Проверяет что:
    - Корректно обрабатывается пустой результат поиска
    - Отправляется информационное сообщение
    - Сообщение содержит указание на отсутствие результатов
    """
    bot.vk_handler.find_potential_matches.return_value = []

    with patch.object(bot, 'send_message') as mock_send:
        bot.handle_find_pair(123)
        mock_send.assert_called_once()
        # Более гибкая проверка сообщения
        message = mock_send.call_args[0][1].lower()
        assert any(word in message for word in ["найдены", "кандидат", "подходящих"])
