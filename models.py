'''SQLAlchemy-модель таблицы оценок студентов.'''

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    '''Базовый класс ORM-моделей.'''


class Student(Base):
    '''
    Строка таблицы: оценка студента по курсу.

    Одному студенту может соответствовать несколько записей —
    по одной на каждый пройденный курс.
    '''

    __tablename__ = 'students'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    faculty: Mapped[str] = mapped_column(String, nullable=False)
    course: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)

    def __str__(self) -> str:
        return (
            f'{self.last_name} {self.first_name} ({self.faculty}), '
            f'{self.course} — {self.grade} баллов'
        )
