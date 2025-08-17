import pytest
from sqlalchemy import inspect

from src.db import queries
from src.db.db_session import Session, init_db
from src.db.vkinder_models import Users


def clear_database(db):
    """
    Удаляет все записи из всех таблиц в базе данных для очистки тестового окружения.

    Args:
        db (Session): Активная сессия SQLAlchemy
    """
    from src.db.vkinder_models import Favorites, Budding_photo, Budding

    db.query(Favorites).delete(synchronize_session=False)
    db.query(Budding_photo).delete(synchronize_session=False)
    db.query(Budding).delete(synchronize_session=False)
    db.query(Users).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(scope='module', autouse=True)
def setup_database():
    """
    Фикстура pytest для настройки тестовой базы данных.

    Действия:
    1. Инициализирует БД (создает таблицы)
    2. Запускает тесты (yield)
    3. Очищает БД после завершения тестов

    Scope:
        module - выполняется один раз для всего модуля тестов
    Autouse:
        True - автоматически используется всеми тестами модуля
    """
    init_db()
    yield
    session = Session()
    try:
        clear_database(session)
    finally:
        session.close()


# python -m pytest ./tests/unit/db/test_db.py -k test_tables_created
def test_tables_created():
    """
    Проверяет, что все ожидаемые таблицы были созданы в БД.

    Assertions:
        - Таблица 'users' существует
        - Таблица 'budding' существует
        - Таблица 'favorites' существует
        - Таблица 'budding_photo' существует
    """
    inspector = inspect(Session().bind)
    tables = inspector.get_table_names()
    assert 'users' in tables
    assert 'budding' in tables
    assert 'favorites' in tables
    assert 'budding_photo' in tables


# python -m pytest ./tests/unit/db/test_db.py -k test_add_and_get_user
def test_add_and_get_user():
    """
    Тестирует добавление и получение пользователя из БД.

    Arrange:
        - Создаем тестовые данные пользователя
    Act:
        - Добавляем пользователя через add_user
        - Получаем его через get_user_by_id
    Assert:
        - Проверяем, что пользователь был корректно сохранен и получен
    """
    session = Session()
    try:
        user_data = {
            "user_id": 123456,
            "first_name": "Test",
            "last_name": "User",
            "gender": "other",
            "age": 25,
            "url_profile": "https://vk.com/testuser",
            "city": "TestCity"
        }
        user = Users(**user_data)
        session.add(user)
        session.commit()

        got_user = session.query(Users).filter(Users.user_id == 123456).first()

        assert got_user is not None
        assert got_user.first_name == "Test"
        assert got_user.url_profile == "https://vk.com/testuser"
    finally:
        session.rollback()
        session.close()


# python -m pytest ./tests/unit/db/test_db.py -k test_queries_add_user_and_related_functions
def test_queries_add_user_and_related_functions():
    """
    Тестирует полный цикл работы с пользователем:
    1. Добавление пользователя
    2. Получение пользователя по ID
    3. Получение пользователя по URL профиля

    Assertions:
        - Пользователь корректно добавляется
        - Пользователь корректно извлекается
        - Все поля сохраняются правильно
    """
    session = Session()
    try:
        user_data = {
            "user_id": 123456,
            "first_name": "FunctionTest",
            "last_name": "User",
            "gender": "other",
            "age": 30,
            "url_profile": "https://vk.com/functiontest",
            "city": "TestCity"
        }

        user = queries.add_user(session, user_data)

        fetched = queries.get_user_by_id(session, user.user_id)
        assert fetched is not None
        assert fetched.first_name == "FunctionTest"

        fetched_by_url = queries.get_user_by_profile_url(session, user_data['url_profile'])
        assert fetched_by_url is not None
        assert fetched_by_url.user_id == user_data['user_id']

    finally:
        session.rollback()
        session.close()


# python -m pytest ./tests/unit/db/test_db.py -k test_queries_budding_and_favorites_flow
def test_queries_budding_and_favorites_flow():
    """
    Тестирует полный цикл работы с кандидатами и избранным:
    1. Добавление кандидата
    2. Добавление в избранное
    3. Проверка избранного
    4. Удаление из избранного

    Assertions:
        - Все операции выполняются без ошибок
        - Состояние БД соответствует ожиданиям на каждом этапе
    """
    session = Session()
    try:
        budding_data = {
            "budding_id": 1,
            "first_name": "Candidate",
            "last_name": "Example",
            "gender": "female",
            "age": 27,
            "url_profile": "https://vk.com/candidate",
            "city": "City"
        }

        bud = queries.add_budding(session, budding_data)
        assert bud.budding_id == 1

        fav = queries.add_favorite(session, user_id=123456, budding_id=1)
        assert fav.user_id == 123456
        assert fav.budding_id == 1

        favorites_list = queries.get_favorites_for_user(session, user_id=123456)
        assert any(f.budding_id == 1 for f in favorites_list)

        removed = queries.remove_favorite(session, user_id=123456, budding_id=1)
        assert removed is True

        favorites_after_removal = queries.get_favorites_for_user(session, user_id=123456)
        assert all(f.budding_id != 1 for f in favorites_after_removal)

    finally:
        session.rollback()
        session.close()


# python -m pytest ./tests/unit/db/test_db.py -k test_queries_budding_photo_and_top_photos
def test_queries_budding_photo_and_top_photos():
    """
    Тестирует работу с фотографиями кандидатов:
    1. Добавление нескольких фото
    2. Получение топ-N фото
    3. Проверка сортировки по рангу

    Assertions:
        - Возвращается правильное количество фото
        - Фото отсортированы по рангу (rank_photo)
    """
    session = Session()
    try:
        photos = [
            {"budding_id": 1, "photo_vk": "photo1", "likes_count": 5, "rank_photo": 2},
            {"budding_id": 1, "photo_vk": "photo2", "likes_count": 15, "rank_photo": 1},
            {"budding_id": 1, "photo_vk": "photo3", "likes_count": 7, "rank_photo": 3},
        ]

        for photo in photos:
            queries.add_budding_photo(session, photo)

        top_photos = queries.get_top_photos_for_budding(session, budding_id=1, limit=2)
        assert len(top_photos) == 2
        ranks = [p.rank_photo for p in top_photos]
        assert ranks == sorted(ranks)

    finally:
        session.rollback()
        session.close()
