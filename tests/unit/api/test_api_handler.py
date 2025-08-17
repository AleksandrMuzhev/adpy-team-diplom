from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.vk_api_handler import VKAPIHandler
from src.vk_api_handler import VKUser


class TestVKAPIHandler:
    @pytest.fixture
    def handler(self):
        """Создает и возвращает мок-объект VKAPIHandler для тестирования.

        Returns:
            VKAPIHandler: Тестовый экземпляр обработчика API ВКонтакте с мокированным API.
        """
        with patch('src.vk_api_handler.vk_api.VkApi') as mock_vk:
            mock_api = MagicMock()
            mock_vk.return_value.get_api.return_value = mock_api
            handler = VKAPIHandler("test_token", 123)
            handler.api = mock_api
            return handler

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_get_user_info_success
    def test_get_user_info_success(self, handler, mock_user_data):
        """Тестирует успешное получение информации о пользователе.

        Args:
            handler: Мок-объект VKAPIHandler
            mock_user_data: Фикстура с тестовыми данными пользователя
        """
        handler.api.users.get.return_value = [mock_user_data]
        user = handler.get_user_info(1)
        assert user.first_name == 'Test'

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_get_user_info_error
    def test_get_user_info_error(self, handler):
        """Тестирует обработку ошибки при получении информации о пользователе.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.users.get.side_effect = Exception("API error")
        user = handler.get_user_info(1)
        assert user is None

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_find_matches_with_interests
    def test_find_matches_with_interests(self, handler):
        """Тестирует поиск совпадений с учетом интересов пользователя.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.users.search.return_value = {
            'items': [{
                'id': 101,
                'first_name': 'Anna',
                'last_name': 'Petrova',
                'sex': 1,
                'city': {'id': 1, 'title': 'Moscow'},
                'domain': 'petrova',
                'is_closed': False,
                'music': 'rock, pop',
                'books': 'sci-fi, fantasy',
                'interests': 'programming',
                'bdate': '01.01.1995',
                'movies': ''
            }]
        }

        user = VKUser(
            id=123,
            first_name="Test",
            last_name="User",
            age=30,
            city="Moscow",
            sex=2,
            profile_url="https://vk.com/testuser"
        )
        user.interests = {
            'music': 'rock, jazz',
            'books': 'sci-fi',
            'interests': 'programming',
            'movies': ''
        }

        matches = handler.find_potential_matches(user)
        assert len(matches) == 1

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_get_top_photos_empty
    def test_get_top_photos_empty(self, handler):
        """Тестирует получение топ-фотографий, когда у пользователя нет фотографий.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.photos.get.return_value = {'items': []}
        photos = handler.get_top_photos(1)
        assert photos == []

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_get_top_photos_with_results
    def test_get_top_photos_with_results(self, handler):
        """Тестирует успешное получение топ-фотографий пользователя.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.photos.get.return_value = {
            'items': [
                {
                    'id': 1,
                    'likes': {'count': 10},
                    'sizes': [{'type': 'm', 'url': 'http://photo1'}],
                    'owner_id': 123
                },
                {
                    'id': 2,
                    'likes': {'count': 5},
                    'sizes': [{'type': 'm', 'url': 'http://photo2'}],
                    'owner_id': 123
                }
            ]
        }
        photos = handler.get_top_photos(123)
        assert len(photos) == 2
        assert photos[0]['id'] == 1
        assert 'url' in photos[0]

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_like_photo_success
    def test_like_photo_success(self, handler):
        """Тестирует успешную установку лайка на фотографию.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.likes.add.return_value = True
        result = handler.like_photo(123, 456)
        assert result is True

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_like_photo_error
    def test_like_photo_error(self, handler):
        """Тестирует обработку ошибки при установке лайка на фотографию.

        Args:
            handler: Мок-объект VKAPIHandler
        """
        handler.api.likes.add.side_effect = Exception("Like failed")
        result = handler.like_photo(123, 456)
        assert result is False

    # python -m pytest ./tests/unit/api/test_api_handler.py -k test_age_parsing
    @patch('datetime.datetime')
    def test_age_parsing(self, mock_datetime):
        """Тестирует корректность парсинга возраста из даты рождения.

        Args:
            mock_datetime: Мок-объект datetime для управления текущей датой в тестах
        """
        mock_datetime.now.return_value = datetime(2025, 1, 1)
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        handler = VKAPIHandler("group_token", 123)
        assert handler._parse_age("01.01.1990") == 35
        assert handler._parse_age("15.08") is None
        assert handler._parse_age(None) is None
