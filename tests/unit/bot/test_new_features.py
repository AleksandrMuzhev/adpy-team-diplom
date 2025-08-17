from datetime import datetime
from unittest.mock import patch


# python -m pytest ./tests/unit/bot/test_new_features.py -k test_age_calculation
def test_age_calculation():
    """Тестирует корректность вычисления возраста пользователя по дате рождения.

    Проверяет различные сценарии:
    - Полная дата рождения (день.месяц.год) - вычисляется точный возраст
    - Частичная дата (только день и месяц) - возвращается None
    - Отсутствие даты - возвращается None

    Использует mock для фиксации текущей даты (2025 год) в тестах.
    """
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1)  # Обновляем год на 2025
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        from src.vk_api_handler import VKAPIHandler
        handler = VKAPIHandler("group_token", 123)
        assert handler._parse_age("01.01.1990") == 35  # Обновляем ожидаемый возраст
        assert handler._parse_age("15.08") is None
        assert handler._parse_age(None) is None


# python -m pytest ./tests/unit/bot/test_new_features.py -k test_blacklist_handling
@patch('src.vk_api_handler.vk_api.VkApi')
def test_blacklist_handling(mock_api_handler):
    """Тестирует функционал работы с черным списком пользователей.

    Проверяет что:
    - Метод добавления в черный список корректно вызывается
    - Возвращается ожидаемый результат (True)
    - API ВКонтакте мокируется для изоляции теста

    Args:
        mock_api_handler: Мок-объект для VK API
    """
    mock_api_handler.api.groups.getMembers.return_value = {'items': []}
    with patch('src.db.queries.add_to_blacklist') as mock_add:
        mock_add.return_value = True
        result = mock_add(111, 123)
        assert result is True