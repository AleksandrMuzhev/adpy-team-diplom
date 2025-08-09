import os
import sqlalchemy as db
from dotenv import load_dotenv

load_dotenv()

NAME_DB = os.getenv("DB_NAME", "vkinder_db")
PASSWORD = os.getenv("DB_PASSWORD", "postgres")
LOGIN = os.getenv("DB_USER", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")