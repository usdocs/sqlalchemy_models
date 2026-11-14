'''Подключение к базе данных: движок и фабрика сессий.'''

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Файл базы SQLite создаётся рядом с проектом.
DB_PATH = Path(__file__).resolve().parent / 'students.db'

DATABASE_URL = f'sqlite:///{DB_PATH}'

engine = create_engine(DATABASE_URL)

# expire_on_commit=False: объекты можно использовать и после коммита.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
