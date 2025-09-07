import os
from dotenv import load_dotenv

load_dotenv()


NAME_DB = os.getenv("DB_NAME")
PASSWORD = os.getenv("DB_PASSWORD")
LOGIN = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

def get_database_url() -> str:
    """
    Формирует строку подключения (URL) к PostgreSQL базе данных.

    Использует параметры из переменных окружения:
    имя базы (DB_NAME),
    логин (DB_USER),
    пароль (DB_PASSWORD),
    хост (DB_HOST),
    порт (DB_PORT).

    Формат строки: postgresql://<user>:<password>@<host>:<port>/<database>?client_encoding=utf8

    Returns:
        str: строка подключения к базе данных PostgreSQL с указанием кодировки UTF-8.
    """
    return f"postgresql://{LOGIN}:{PASSWORD}@{DB_HOST}:{DB_PORT}/{NAME_DB}?client_encoding=utf8"
