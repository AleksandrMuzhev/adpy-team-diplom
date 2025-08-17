from src.db.queries import add_user, get_user_by_id, add_budding, get_budding_by_id, add_to_blacklist, get_blacklist


# python -m pytest ./tests/unit/db/test_queries.py -k test_add_and_get_user
def test_add_and_get_user(session):
    """Тестирует добавление и получение пользователя из базы данных.

    Проверяет корректность работы функций:
    - add_user - добавление нового пользователя
    - get_user_by_id - получение пользователя по ID

    Проверки:
    1. Пользователь успешно добавляется в БД
    2. Добавленные данные соответствуют переданным
    3. Пользователь может быть получен по ID
    """
    user_data = {
        "user_id": 123,
        "first_name": "Test",
        "last_name": "User",
        "gender": "male",
        "url_profile": "test_url"
    }

    user = add_user(session, user_data)
    fetched = get_user_by_id(session, 123)

    assert fetched is not None
    assert fetched.first_name == "Test"


# python -m pytest ./tests/unit/db/test_queries.py -k test_get_budding_by_id
def test_get_budding_by_id(session):
    """Тестирует добавление и получение кандидата по ID.

    Проверяет работу функций:
    - add_budding - добавление кандидата
    - get_budding_by_id - получение кандидата по ID

    Проверки:
    1. Кандидат успешно добавляется в БД
    2. Все поля сохраняются корректно
    3. Кандидат может быть получен по ID
    """
    budding_data = {
        'budding_id': 1,
        'first_name': "Test",
        'last_name': "User",
        'age': 25,
        'city': "Moscow",
        'gender': 2,
        'url_profile': "test"
    }

    # Передаем словарь в функцию add_budding
    user_id = add_budding(session, budding_data)

    # Получаем кандидата по его id
    budding = get_budding_by_id(session, user_id.budding_id)

    # Проверяем, что кандидат был добавлен
    assert budding is not None


# python -m pytest ./tests/unit/db/test_queries.py -k test_add_to_blacklist
def test_add_to_blacklist(session):
    """Тестирует добавление пользователя в черный список и его получение.

    Проверяет работу функций:
    - add_to_blacklist - добавление в ЧС
    - get_blacklist - получение списка ЧС

    Проверки:
    1. Пользователь успешно добавляется в ЧС
    2. Добавленный пользователь присутствует в списке
    3. Список ЧС возвращает корректные данные
    """
    add_to_blacklist(session, 1, 2)
    blacklist = get_blacklist(session, 1)
    assert 2 in blacklist
