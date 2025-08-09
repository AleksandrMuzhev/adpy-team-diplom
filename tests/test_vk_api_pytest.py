# tests/unit/test_api_handler.py
from datetime import datetime

from src.vk_api_handler import VKAPIHandler, VKUser, VKPhoto


class TestVKAPIHandler:
    def test_find_potential_matches(self, mock_api_handler):
        # Настройка моков
        mock_api_handler.friends.get.side_effect = [
            {'items': [111, 222]},
            {'items': [333, 444]},
            {'items': [555, 666]}
        ]

        mock_api_handler.users.get.side_effect = [
            [{'id': 333, 'first_name': 'Анна', 'last_name': 'Петрова',
              'sex': 1, 'city': {'title': 'Москва'}, 'domain': 'petrova',
              'is_closed': False}],
            [{'id': 555, 'first_name': 'Мария', 'last_name': 'Сидорова',
              'sex': 1, 'city': {'title': 'Москва'}, 'domain': 'sidorova',
              'is_closed': False}]
        ]

        handler = VKAPIHandler("group_token", 123)
        user = VKUser(
            id=123,
            first_name="Иван",
            last_name="Иванов",
            age=30,
            city="Москва",
            sex=2,
            profile_url="https://vk.com/ivanov"
        )

        matches = handler.find_potential_matches(user)
        assert len(matches) == 2
        assert matches[0].first_name == 'Анна'

    class TestVKAPIHandler:
        def test_prepare_attachments(self):
            handler = VKAPIHandler("group_token", 123)  # Убрали group_id
            photos = [
                VKPhoto(id=1, owner_id=123, likes=10, url="test1.jpg", attachment_str="photo123_1"),
                VKPhoto(id=2, owner_id=123, likes=20, url="test2.jpg", attachment_str="photo123_2")
            ]
            assert handler.prepare_attachments(photos) == "photo123_1,photo123_2"

    def test_get_top_photos_empty(self, mock_api_handler):
        mock_api_handler.photos.getUserPhotos.return_value = {'items': []}
        handler = VKAPIHandler("group_token", 123)
        assert len(handler.get_top_photos(123)) == 0

    def test_get_user_info_success(self, mock_api_handler, mock_user_data):
        mock_api_handler.users.get.return_value = [mock_user_data]
        handler = VKAPIHandler("group_token", 123)
        user = handler.get_user_info(123)
        assert user.age == datetime.now().year - 1990

    def test_get_user_info_no_bdate(self, mock_api_handler, mock_user_data):
        mock_user_data.pop('bdate')
        mock_api_handler.users.get.return_value = [mock_user_data]
        handler = VKAPIHandler("group_token", 123)
        assert handler.get_user_info(123).age is None
