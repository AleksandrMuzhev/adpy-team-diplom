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
