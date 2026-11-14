'''Зависимости FastAPI: сессия БД и репозиторий на запрос.'''

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from database import SessionLocal
from repository import StudentRepository


def get_db() -> Generator[Session, None, None]:
    '''Сессия базы на время одного запроса.'''
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_repository(
    db: Session = Depends(get_db),
) -> StudentRepository:
    '''Репозиторий поверх сессии текущего запроса.'''
    return StudentRepository(db)
