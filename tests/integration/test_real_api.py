from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from src.vk_api_handler import VKUser, VKAPIHandler


@pytest.mark.integration
class TestRealAPI:
    # python -m pytest ./tests/integration/test_real_api.py -k test_real_api_call
    def test_real_api_call(self, api_handler):
        """
        Интеграционный тест с реальным VK API (требует валидный токен).

        Note:
            Пропускается, если не удалось получить данные пользователя
        """
        user = api_handler.get_user_info(1)  # ID Дурова
        if user is None:
            pytest.skip("Не удалось получить данные пользователя - возможно, проблемы с токеном")
        assert isinstance(user, VKUser)
        assert user.first_name == 'Павел'
        assert user.profile_url.startswith('https://vk.com/')

    # python -m pytest ./tests/integration/test_real_api.py -k test_mocked_api_call
    def test_mocked_api_call(self):
        """
        Тестирует получение данных пользователя с мокированным API.

        Arrange:
            - Создается мок VK API
            - Настраиваются тестовые данные пользователя
        Act:
            - Вызывается get_user_info()
        Assert:
            - Возвращаемый объект содержит ожидаемые данные
            - Все поля правильно парсятся
        """
        mock_vk = MagicMock()
        mock_api = MagicMock()

        # Настраиваем возвращаемые значения
        mock_vk.get_api.return_value = mock_api
        mock_api.users.get.return_value = [{
            'id': 1,
            'first_name': 'Павел',
            'last_name': 'Дуров',
            'sex': 2,
            'city': {'title': 'Санкт-Петербург'},
            'bdate': '10.10.1984',
            'domain': 'durov',
            'music': '',
            'books': '',
            'movies': '',
            'interests': ''
        }]

        # Создаем тестовый экземпляр с моком
        with patch('vk_api.VkApi', return_value=mock_vk):
            handler = VKAPIHandler(
                group_token="test_token",
                group_id=1,
                user_token="test_user_token"
            )

            # Вызываем метод
            user = handler.get_user_info(1)

            # Проверяем результаты
            assert isinstance(user, VKUser)
            assert user.first_name == 'Павел'
            assert user.last_name == 'Дуров'
            assert user.age == datetime.now().year - 1984
            assert user.city == 'Санкт-Петербург'
            assert user.profile_url == 'https://vk.com/durov'
            assert user.interests == {
                'music': [''],
                'books': [''],
                'movies': [''],
                'interests': ['']
            }
