from unittest.mock import patch
from src.vk_api_handler import VKAPIHandler


class TestVKAPIHandler:
    @patch('src.vk_api_handler.vk_api.VkApi')
    def test_get_user_info(self, mock_vk):
        mock_response = {
            'id': 1,
            'first_name': 'Test',
            'last_name': 'User',
            'sex': 2,
            'city': {'title': 'Moscow'},
            'bdate': '01.01.1990',
            'domain': 'testuser'
        }
        mock_vk.return_value.get_api.return_value.users.get.return_value = [mock_response]

        handler = VKAPIHandler("test_token", 123)
        user = handler.get_user_info(1)

        assert user.first_name == 'Test'
        assert user.profile_url == 'https://vk.com/testuser'