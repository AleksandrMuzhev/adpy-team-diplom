'''
# python -m pytest ./tests/integration/test_db_flow.py -k test_full_db_flow
def test_full_db_flow(session):
    """
    Интеграционный тест полного цикла работы с базой данных.

    Test flow:
        1. Добавление тестового пользователя
        2. Добавление кандидата
        3. Добавление в избранное
        4. Проверка избранного
        5. Удаление из избранного

    Assertions:
        - Все операции выполняются без ошибок
        - Состояние БД соответствует ожиданиям на каждом этапе
        - Финальное состояние БД после удаления

    Fixtures:
        session - предоставляет чистую тестовую БД
    """
    from src.db.queries import (
        add_user, add_budding, add_favorite,
        get_favorites_for_user
    )

    # Создаем тестовые данные в правильном формате
    user_data = {
        'user_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
    }

    # Тест полного цикла работы с БД
    user_id = add_user(session, user_data)

    budding_data = {
        'budding_id': 2,
        'first_name': 'Match',
        'last_name': 'Test',
        'age': 25,
        'city': 'Moscow',
        'sex': 1,
        'profile_url': 'match'
    }
    budding_id = add_budding(session, budding_data)

    add_favorite(session, user_id.user_id, budding_id.budding_id)
    favorites = get_favorites_for_user(session, user_id.user_id)
    assert len(favorites) == 1
'''
import pytest
from sqlalchemy import inspect

def test_full_db_flow(session):
    """
    Интеграционный тест полного цикла работы с базой данных.

    Test flow:
        1. Проверка создания таблиц в базе
        2. Добавление тестового пользователя
        3. Добавление кандидата
        4. Добавление в избранное
        5. Проверка избранного
        6. Удаление из избранного
        7. Проверка отсутствия избранного после удаления

    Assertions:
        - Все операции выполняются без ошибок
        - Состояние БД соответствует ожиданиям на каждом этапе
        - Финальное состояние БД после удаления проверено
    """
    from src.db.queries import add_user, add_budding, add_favorite, get_favorites_for_user, remove_favorite

    # Проверяем, что таблицы созданы
    inspector = inspect(session.bind)
    tables = inspector.get_table_names()
    expected_tables = {'users', 'budding', 'favorites', 'blacklist', 'budding_photo'}
    assert expected_tables.issubset(set(tables)), "Не все необходимые таблицы созданы"

    # Добавляем пользователя
    user_data = {
        'user_id': 1,
        'first_name': 'Test',
        'last_name': 'User',
        'gender': 'male',
        'url_profile': 'http://vk.com/testuser',
        'age': 30,
        'city': 'Moscow'
    }
    user = add_user(session, user_data)
    assert user.user_id == user_data['user_id']

    # Добавляем кандидата
    budding_data = {
        'budding_id': 2,
        'first_name': 'Match',
        'last_name': 'Test',
        'age': 25,
        'city': 'Moscow',
        'gender': 'female',
        'url_profile': 'http://vk.com/matchtest'
    }
    budding = add_budding(session, budding_data)
    assert budding.budding_id == budding_data['budding_id']

    # Добавляем в избранное
    add_favorite(session, user.user_id, budding.budding_id)
    favorites = get_favorites_for_user(session, user.user_id)
    assert len(favorites) == 1

    # Удаляем из избранного
    removed = remove_favorite(session, user.user_id, budding.budding_id)
    assert removed is True

    # Проверяем, что избранного больше нет
    favorites_after = get_favorites_for_user(session, user.user_id)
    assert len(favorites_after) == 0
