from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, inspect
from .model_db import get_database_url
from .vkinder_models import Base
from ..vk_api_handler import logger

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    """
    Инициализирует структуру базы данных, создавая все таблицы, определенные в моделях SQLAlchemy.

    Side effects:
        - Создает все таблицы в подключенной БД
        - Логирует процесс создания таблиц
        - Выводит список созданных таблиц в лог

    Example:
        >>> init_db()
        INFO: Creating tables...
        INFO: Tables created: ['users', 'budding', 'favorites', ...]
    """
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    logger.info(f"Tables created: {inspector.get_table_names()}")