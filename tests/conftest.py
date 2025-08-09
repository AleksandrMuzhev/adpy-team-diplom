import os
from unittest.mock import Mock, patch

import pytest
from dotenv import load_dotenv

from src.vk_api_handler import VKAPIHandler

load_dotenv()


@pytest.fixture
def vk_token():
    token = os.getenv("VK_TOKEN")
    if not token:
        pytest.skip("Требуется VK_TOKEN в .env")
    return token


@pytest.fixture
def group_id():
    return int(os.getenv("GROUP_ID", 0))


@pytest.fixture
def api_handler(vk_token, group_id):
    return VKAPIHandler(vk_token, group_id)


@pytest.fixture
def mock_user_data():
    return {
        'id': 123,
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'sex': 2,
        'city': {'title': 'Москва'},
        'bdate': '01.01.1990',
        'domain': 'ivanov'
    }


@pytest.fixture
def mock_api_handler():
    with patch('src.vk_api_handler.vk_api.VkApi') as mock_vk:
        mock_api = Mock()
        mock_vk.return_value.get_api.return_value = mock_api
        yield mock_api
