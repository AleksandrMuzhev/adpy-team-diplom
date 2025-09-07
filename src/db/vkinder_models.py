import sqlalchemy as db
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Users(Base):
    """
    Модель пользователя в базе данных.

    Атрибуты:
        user_id (int): Уникальный идентификатор пользователя (PK).
        first_name (str): Имя пользователя.
        last_name (str): Фамилия пользователя.
        gender (str): Пол пользователя.
        age (int, optional): Возраст пользователя.
        url_profile (str): URL профиля пользователя (уникальный).
        city (str, optional): Город пользователя.
        favorites (list): Связь с избранными кандидатами (Favorites).
    """
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True, nullable=False)
    first_name = db.Column(db.String(length=40), nullable=False)
    last_name = db.Column(db.String(length=40), nullable=False)
    gender = db.Column(db.String(length=7), nullable=False)
    age = db.Column(db.Integer)
    url_profile = db.Column(db.String(length=200), nullable=False, unique=True)
    city = db.Column(db.String(length=200))

    favorites = relationship(
        'Favorites',
        back_populates='users',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Favorites(Base):
    """
    Модель избранных кандидатов пользователя.

    Атрибуты:
        id (int): Уникальный идентификатор записи (PK).
        user_id (int): Внешний ключ на пользователя.
        budding_id (int): Внешний ключ на кандидата.
        add_date (datetime): Дата добавления в избранное.
        users: Обратная связь с пользователем (Users).
        budding: Обратная связь с кандидатом (Budding).
    """
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    budding_id = db.Column(db.Integer, db.ForeignKey('budding.budding_id', ondelete='CASCADE'), nullable=False)

    add_date = db.Column(db.DateTime, server_default=func.now())

    users = relationship('Users', back_populates='favorites')
    budding = relationship('Budding', back_populates='favorites')


class Budding(Base):
    """
    Модель кандидата.

    Атрибуты:
        budding_id (int): Уникальный идентификатор кандидата (PK).
        first_name (str): Имя кандидата.
        last_name (str): Фамилия кандидата.
        gender (str): Пол кандидата.
        age (int, optional): Возраст кандидата.
        url_profile (str): URL профиля кандидата (уникальный).
        city (str, optional): Город кандидата.
        favorites (list): Связь с пользователями, у которых кандидат в избранном.
        budding_photo (list): Связь с фотографиями кандидата.
    """
    __tablename__ = 'budding'

    budding_id = db.Column(db.Integer, primary_key=True, nullable=False)
    first_name = db.Column(db.String(length=40), nullable=False)
    last_name = db.Column(db.String(length=40), nullable=False)
    gender = db.Column(db.String(length=7), nullable=False)
    age = db.Column(db.Integer)
    url_profile = db.Column(db.String(length=200), nullable=False, unique=True)
    city = db.Column(db.String(length=200))

    favorites = relationship(
        'Favorites',
        back_populates='budding',
        cascade='all, delete-orphan',
        passive_deletes=True
    )
    budding_photo = relationship(
        'Budding_photo',
        back_populates='budding',
        cascade='all, delete-orphan',
        passive_deletes=True
    )


class Budding_photo(Base):
    """
    Модель фотографии кандидата.

    Атрибуты:
        photo_id (int): Уникальный идентификатор фотографии (PK).
        budding_id (int): Внешний ключ на кандидата.
        photo_vk (str): Ссылка на фото ВК.
        likes_count (int): Количество лайков.
        rank_photo (int): Ранг фотографии для показа.
        budding: Обратная связь с кандидатом (Budding).
    """
    __tablename__ = 'budding_photo'

    photo_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    budding_id = db.Column(db.Integer, db.ForeignKey('budding.budding_id', ondelete='CASCADE'), nullable=False)
    photo_vk = db.Column(db.String(length=200), nullable=False)
    likes_count = db.Column(db.Integer)
    rank_photo = db.Column(db.Integer, nullable=False)

    budding = relationship('Budding', back_populates='budding_photo')


class Blacklist(Base):
    """
    Модель чёрного списка пользователя.

    Атрибуты:
        id (int): Уникальный идентификатор записи (PK).
        user_id (int): Внешний ключ на пользователя.
        blocked_id (int): ID заблокированного пользователя.
        block_date (datetime): Дата блокировки.
        user: Обратная связь с пользователем (Users).
    """
    __tablename__ = 'blacklist'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'))
    blocked_id = db.Column(db.Integer, nullable=False)
    block_date = db.Column(db.DateTime, server_default=func.now())

    # Связь с пользователем
    user = relationship("Users", backref="blacklists")
