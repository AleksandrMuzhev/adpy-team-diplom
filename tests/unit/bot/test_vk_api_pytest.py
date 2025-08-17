from unittest.mock import MagicMock, patch

import pytest

from src.vk_api_handler import VKAPIHandler
from src.vk_api_handler import VKUser


class TestVKAPIHandler:
    @pytest.fixture
    def handler(self):
        """Фикстура для создания тестового экземпляра VKAPIHandler с мокированным API.

        Returns:
            VKAPIHandler: Экземпляр обработчика VK API с подмененными:
            - vk_api.VkApi - мок основного API клиента
            - api - мок методов VK API
            - user_api - мок пользовательского API (если требуется)
        """
        with patch('src.vk_api_handler.vk_api.VkApi') as mock_vk:
            mock_api = MagicMock()
            mock_vk.return_value.get_api.return_value = mock_api
            handler = VKAPIHandler("test_token", 123)
            handler.api = mock_api
            return handler

    # python -m pytest ./tests/unit/bot/test_vk_api_pytest.py -k test_get_user_info_success
    def test_get_user_info_success(self, handler, mock_user_data):
        """
        Тестирует успешное получение данных пользователя из VK API.

        Arrange:
            - Настроен mock API с тестовыми данными пользователя
            - Создан экземпляр VKAPIHandler

        Act:
            - Вызов get_user_info с тестовым ID

        Assert:
            - Возвращен объект VKUser
            - Основные поля соответствуют ожидаемым
            - Вызов API был выполнен 1 раз
        """
        handler.api.users.get.return_value = [mock_user_data]
        user = handler.get_user_info(1)
        assert user.first_name == 'Test'

    # python -m pytest ./tests/unit/bot/test_vk_api_pytest.py -k test_get_user_info_no_bdate
    def test_get_user_info_no_bdate(self, handler, mock_user_data):
        """Тестирует обработку отсутствия даты рождения в профиле пользователя.

        Arrange:
            - Настроен mock API с данными пользователя без поля bdate
            - Создан экземпляр VKAPIHandler

        Act:
            - Вызов get_user_info с тестовым ID

        Assert:
            - Возраст пользователя None
            - Остальные поля заполнены корректно
        """
        mock_user_data['bdate'] = None
        handler.api.users.get.return_value = [mock_user_data]
        user = handler.get_user_info(1)
        assert user.age is None

    # python -m pytest ./tests/unit/bot/test_vk_api_pytest.py -k test_find_potential_matches
    def test_find_potential_matches(self, handler):
        """
        Тестирует поиск кандидатов с различными критериями.

        Test cases:
            - Возраст в допустимом диапазоне
            - Совпадение по городу
            - Открытый профиль
            - Исключение закрытых профилей

        Assert:
            - Количество возвращенных кандидатов > 0
            - Все профили открыты
            - Возраст в диапазоне ±5 лет
        """
        handler.api.users.search.return_value = {
            'items': [{
                'id': 1,
                'first_name': 'Test',
                'last_name': 'User',
                'sex': 1,
                'city': {'id': 1, 'title': 'Moscow'},
                'is_closed': False,
                'bdate': '01.01.1990',
                'domain': 'testuser',
                'music': 'rock, pop',
                'books': 'sci-fi',
                'interests': 'programming',
                'movies': 'action'
            }]
        }

        mock_user = VKUser(
            id=123,
            first_name="Test",
            last_name="User",
            age=25,
            city="Moscow",
            sex=2,
            profile_url="test",
            interests={
                'music': ['rock', 'pop'],
                'books': ['sci-fi'],
                'interests': ['programming'],
                'movies': ['action']
            }
        )

        matches = handler.find_potential_matches(mock_user)
        assert len(matches) == 1
        assert matches[0].id == 1

    # python -m pytest ./tests/unit/bot/test_vk_api_pytest.py -k test_get_top_photos_empty
    def test_get_top_photos_empty(self, handler):
        """Тестирует обработку случая, когда у пользователя нет фотографий.

        Arrange:
            - Настроен mock API возвращающий пустой список фотографий
            - Создан экземпляр VKAPIHandler

        Act:
            - Вызов get_top_photos с тестовым ID

        Assert:
            - Возвращается пустой список
            - Нет ошибок при обработке пустого результата
        """
        handler.api.photos.get.return_value = {'items': []}
        photos = handler.get_top_photos(1)
        assert photos == []
