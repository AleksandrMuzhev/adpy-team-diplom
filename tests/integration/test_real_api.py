import pytest


@pytest.mark.integration
class TestRealAPI:
    def test_real_api_call(self, api_handler):
        # Тестируем только с реальным токеном
        user = api_handler.get_user_info(1)  # ID Дурова
        if user is None:
            pytest.skip("Не удалось получить данные пользователя - возможно, проблемы с токеном")
        assert user.first_name == 'Павел'
        assert user.profile_url.startswith('https://vk.com/')
