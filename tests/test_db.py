import pytest
from sqlalchemy import inspect
from src.db.db_session import Session, init_db
from src.db.vkinder_models import Users
from src.db import queries


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
    init_db()
    yield
    session = Session()
    try:
        clear_database(session)
    finally:
        session.close()


def test_tables_created():
    inspector = inspect(Session().bind)
    tables = inspector.get_table_names()
    assert 'users' in tables
    assert 'budding' in tables
    assert 'favorites' in tables
    assert 'budding_photo' in tables


def test_add_and_get_user():
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


def test_queries_add_user_and_related_functions():
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


def test_queries_budding_and_favorites_flow():
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


def test_queries_budding_photo_and_top_photos():
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
