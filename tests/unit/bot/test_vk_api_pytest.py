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

    def test_get_user_info_success(self, handler, mock_user_data):
        """Тестирует успешное получение данных пользователя из VK API."""
        handler.api.users.get.return_value = [mock_user_data]
        user = handler.get_user_info(1)
        assert user.first_name == 'Test'

    def test_get_user_info_no_bdate(self, handler, mock_user_data):
        """Тестирует обработку отсутствия даты рождения в профиле пользователя."""
        mock_user_data['bdate'] = None
        handler.api.users.get.return_value = [mock_user_data]
        user = handler.get_user_info(1)
        assert user.age is None

    def test_find_potential_matches(self, handler):
        """Тестирует поиск кандидатов с различными критериями."""
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

    def test_get_top_photos_empty(self, handler):
        """Тестирует обработку случая, когда у пользователя нет фотографий."""
        handler.api.photos.get.return_value = {'items': []}
        photos = handler.get_top_photos(1)
        assert photos == []

    def test_unlike_photo_success(self, handler):
        """Тестирует успешное удаление лайка с фото."""
        handler.user_api = MagicMock()
        handler.user_api.likes.delete.return_value = {}

        result = handler.unlike_photo(photo_id=123, owner_id=456)
        assert result is True
        handler.user_api.likes.delete.assert_called_once_with(type='photo', owner_id=456, item_id=123)

    def test_unlike_photo_no_user_api(self, handler):
        """Тестирует удаление лайка при отсутствии user_api (токена пользователя)."""
        handler.user_api = None
        assert handler.unlike_photo(photo_id=123, owner_id=456) is False

    def test_get_all_members(self, handler):
        """Тестирует получение всех участников группы с обработкой пагинации."""
        handler.api.groups.getMembers.side_effect = [
            {'items': [{'id': 1}, {'id': 2}]},
            {'items': []}
        ]
        members = handler.get_all_members()
        assert len(members) == 2

    def test_get_common_interests_success(self, handler):
        """Тестирует вычисление процента общих групп при успешном вызове."""
        handler.api.groups.get.side_effect = [
            {'items': {1, 2, 3}},
            {'items': {2, 3, 4}},
        ]
        score = handler.get_common_interests(user_id=1, candidate_id=2)
        assert abs(score - 2/3) < 0.01

    def test_get_common_interests_exception(self, handler):
        """Тестирует обработку исключения при получении групп (возвращает 0.0)."""
        handler.api.groups.get.side_effect = Exception("api failure")
        score = handler.get_common_interests(user_id=1, candidate_id=2)
        assert score == 0
