from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from .vkinder_models import Users, Budding, Budding_photo, Favorites, Blacklist
from ..vk_api_handler import logger


def add_user(db: Session, user: dict) -> Users:
    """
    Добавляет нового пользователя или обновляет существующего в базе.

    Args:
        db (Session): сессия базы данных.
        user (dict): данные пользователя.

    Returns:
        Users: объект пользователя из базы.
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
    Получает пользователя по ID.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя.

    Returns:
        Optional[Users]: объект пользователя или None.
    """
    try:
        return db.query(Users).filter(Users.user_id == user_id).first()
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error при get_user_by_id user_id={user_id}: {e}")
        return None


def get_user_by_profile_url(db: Session, url: str) -> Optional[Users]:
    """
    Получает пользователя по URL профиля.

    Args:
        db (Session): сессия базы данных.
        url (str): URL профиля пользователя.

    Returns:
        Optional[Users]: объект пользователя или None.
    """
    try:
        return db.query(Users).filter(Users.url_profile == url).first()
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error при get_user_by_profile_url url={url}: {e}")
        return None


def add_budding(db: Session, budding: dict) -> Budding:
    """
    Добавляет или обновляет запись кандидата в базе.

    Args:
        db (Session): сессия базы данных.
        budding (dict): данные кандидата.

    Returns:
        Budding: объект кандидата.
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
    Добавляет фотографию кандидата.

    Args:
        db (Session): сессия базы данных.
        photo (dict): данные фотографии.

    Returns:
        Budding_photo: объект фотографии.
    """
    new = Budding_photo(**photo)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


def get_budding_by_id(db: Session, budding_id: int) -> Optional[Budding]:
    """
    Получает кандидата по ID.

    Args:
        db (Session): сессия базы данных.
        budding_id (int): ID кандидата.

    Returns:
        Optional[Budding]: объект кандидата или None.
    """
    try:
        return db.query(Budding).filter(Budding.budding_id == budding_id).first()
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error при get_budding_by_id budding_id={budding_id}: {e}")
        return None


def add_favorite(db: Session, user_id: int, budding_id: int) -> Favorites:
    """
    Добавляет кандидата в избранное пользователя.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя.
        budding_id (int): ID кандидата.

    Returns:
        Favorites: объект избранного.
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
    Удаляет кандидата из избранного пользователя.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя.
        budding_id (int): ID кандидата.

    Returns:
        bool: True, если удаление успешно, False если запись отсутствует.
    """
    fav = db.query(Favorites).filter(Favorites.user_id == user_id, Favorites.budding_id == budding_id).first()
    if not fav:
        return False
    db.delete(fav)
    db.commit()
    return True


def get_favorites_for_user(db: Session, user_id: int) -> List[Budding]:
    """
    Получает список кандидатов, добавленных в избранное пользователя.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя.

    Returns:
        List[Budding]: список кандидатов.
    """
    try:
        return db.query(Budding) \
            .join(Favorites, Budding.budding_id == Favorites.budding_id) \
            .filter(Favorites.user_id == user_id) \
            .all()
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error при get_favorites_for_user user_id={user_id}: {e}")
        return []


def get_top_photos_for_budding(db: Session, budding_id: int, limit: int = 3) -> List[Budding_photo]:
    """
    Получает топ фотографий для кандидата, отсортированных по рангу.

    Args:
        db (Session): сессия базы данных.
        budding_id (int): ID кандидата.
        limit (int): максимальное количество фотографий.

    Returns:
        List[Budding_photo]: список фотографий.
    """
    try:
        return db.query(Budding_photo) \
            .filter(Budding_photo.budding_id == budding_id) \
            .order_by(Budding_photo.rank_photo) \
            .limit(limit) \
            .all()
    except UnicodeDecodeError as e:
        logger.error(f"Unicode decode error при get_top_photos_for_budding budding_id={budding_id}: {e}")
        return []


def add_to_blacklist(db: Session, user_id: int, blocked_id: int):
    """
    Добавляет пользователя в чёрный список.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя, добавляющего в чёрный список.
        blocked_id (int): ID пользователя, которого блокируют.
    """
    try:
        blocked_id_int = int(blocked_id)
        db.add(Blacklist(user_id=user_id, blocked_id=blocked_id_int))
        db.commit()
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid blocked_id: {blocked_id}, error: {e}")
        db.rollback()


def get_blacklist(db: Session, user_id: int) -> List[int]:
    """
    Получает список ID пользователей из чёрного списка.

    Args:
        db (Session): сессия базы данных.
        user_id (int): ID пользователя.

    Returns:
        List[int]: список ID заблокированных пользователей.
    """
    try:
        result = []
        rows = db.query(Blacklist).filter(Blacklist.user_id == user_id).all()
        logger.info(f"Found {len(rows)} blacklist entries for user {user_id}")

        for i, row in enumerate(rows):
            try:
                if isinstance(row.blocked_id, bytes):
                    blocked_id = row.blocked_id.decode('utf-8', errors='ignore')
                else:
                    blocked_id = row.blocked_id

                blocked_id_int = int(blocked_id)
                result.append(blocked_id_int)
            except (ValueError, TypeError, UnicodeDecodeError) as e:
                logger.error(f'Error in row {i}: blocked_id={repr(row.blocked_id)}, error: {e}')
                continue
        return result
    except Exception as e:
        logger.error(f"Error getting blacklist: {e}")
        return []
