from sqlalchemy.orm import Session
from .vkinder_models import Users, Budding, Budding_photo, Favorites
from typing import List, Optional
from datetime import datetime


def add_user(db: Session, user: dict) -> Users:
    """
    Добавляет нового пользователя в базу данных или обновляет существующего.

    Args:
        db (Session): Активная сессия SQLAlchemy для работы с БД.
        user (dict): Словарь с данными пользователя. Должны быть ключи:
            'user_id', 'first_name', 'last_name', 'gender', 'age', 'url_profile', 'city'.

    Returns:
        Users: Объект пользователя из базы (новый или обновлённый).

    Логика:
        - Проверяем, есть ли пользователь с user_id в базе.
        - Если есть, обновляем его поля.
        - Если нет, создаём новую запись.
        - Сохраняем изменения и возвращаем объект.
    """
    existing = db.query(Users).filter(Users.user_id == user['user_id']).first()
    if existing:
        for k, v in user.items():
            setattr(existing, k, v)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    new = Users(**user)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def get_user_by_id(db: Session, user_id: int) -> Optional[Users]:
    """
    Получить пользователя по его user_id.

    Args:
        db (Session): Активная сессия работы с БД.
        user_id (int): Идентификатор пользователя.

    Returns:
        Optional[Users]: Объект пользователя или None, если не найден.
    """
    return db.query(Users).filter(Users.user_id == user_id).first()


def get_user_by_profile_url(db: Session, url: str) -> Optional[Users]:
    """
    Получить пользователя по URL профиля.

    Args:
        db (Session): Сессия БД.
        url (str): URL профиля (уникальный).

    Returns:
        Optional[Users]: Объект пользователя или None.
    """
    return db.query(Users).filter(Users.url_profile == url).first()


def add_budding(db: Session, budding: dict) -> Budding:
    """
    Добавить или обновить кандидата (Budding).

    Args:
        db (Session): Сессия БД.
        budding (dict): Данные кандидата с ключами, например:
            'budding_id', 'first_name', 'last_name', 'gender', 'age', 'url_profile', 'city'.

    Returns:
        Budding: Объект кандидата (новый или обновлённый).
    """
    existing = db.query(Budding).filter(Budding.budding_id == budding['budding_id']).first()
    if existing:
        for k, v in budding.items():
            setattr(existing, k, v)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    new = Budding(**budding)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def add_budding_photo(db: Session, photo: dict) -> Budding_photo:
    """
    Добавить фотографию кандидата.

    Args:
        db (Session): Сессия БД.
        photo (dict): Данные фото, например:
            'budding_id', 'photo_vk', 'likes_count', 'rank_photo'.

    Returns:
        Budding_photo: Добавленная запись фотографии.
    """
    new = Budding_photo(**photo)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def get_budding_by_id(db: Session, budding_id: int) -> Optional[Budding]:
    """
    Получить кандидата по его id.

    Args:
        db (Session): Сессия БД.
        budding_id (int): Идентификатор кандидата.

    Returns:
        Optional[Budding]: Объект кандидата или None.
    """
    return db.query(Budding).filter(Budding.budding_id == budding_id).first()


def add_favorite(db: Session, user_id: int, budding_id: int) -> Favorites:
    """
    Добавить запись в избранное: пользователь добавляет кандидата.

    Args:
        db (Session): Сессия БД.
        user_id (int): ID пользователя.
        budding_id (int): ID кандидата.

    Returns:
        Favorites: Объект добавленной записи избранного.
        Если такая запись уже есть — возвращает её.
    """
    existing = db.query(Favorites).filter(Favorites.user_id == user_id, Favorites.budding_id == budding_id).first()
    if existing:
        return existing
    fav = Favorites(user_id=user_id, budding_id=budding_id, add_date=datetime.now())
    db.add(fav)
    db.commit()
    db.refresh(fav)
    return fav


def remove_favorite(db: Session, user_id: int, budding_id: int) -> bool:
    """
    Удалить запись избранного пользователя.

    Args:
        db (Session): Сессия БД.
        user_id (int): ID пользователя.
        budding_id (int): ID кандидата.

    Returns:
        bool: True — если запись удалена, False — если её не было.
    """
    fav = db.query(Favorites).filter(Favorites.user_id == user_id, Favorites.budding_id == budding_id).first()
    if not fav:
        return False
    db.delete(fav)
    db.commit()
    return True


def get_favorites_for_user(db: Session, user_id: int) -> List[Budding]:
    """
    Получить список избранных кандидатов конкретного пользователя.

    Args:
        db (Session): Сессия БД.
        user_id (int): ID пользователя.

    Returns:
        List[Budding]: Список объектов Budding — кандидатов, добавленных в избранное.
    """
    return db.query(Budding) \
             .join(Favorites, Budding.budding_id == Favorites.budding_id) \
             .filter(Favorites.user_id == user_id) \
             .all()


def get_top_photos_for_budding(db: Session, budding_id: int, limit: int = 3) -> List[Budding_photo]:
    """
    Получить топ-N фотографий кандидата, отсортированных по рангу.

    Args:
        db (Session): Сессия БД.
        budding_id (int): ID кандидата.
        limit (int): Максимальное количество фото, по умолчанию 3.

    Returns:
        List[Budding_photo]: Список фото, отсортированных по возрастанию rank_photo.
    """
    return db.query(Budding_photo) \
             .filter(Budding_photo.budding_id == budding_id) \
             .order_by(Budding_photo.rank_photo) \
             .limit(limit) \
             .all()
