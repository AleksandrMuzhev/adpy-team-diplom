from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from .model_db import get_database_url
from .vkinder_models import Base

DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)