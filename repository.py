'''Класс для операций INSERT и SELECT над моделью Student.'''

import csv
import logging
from collections.abc import Iterable, Mapping
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Student

logger = logging.getLogger(__name__)

# Заголовок students.csv должен быть именно таким.
EXPECTED_HEADER = ['Фамилия', 'Имя', 'Факультет', 'Курс', 'Оценка']

# Допустимый диапазон оценки (баллы).
GRADE_MIN, GRADE_MAX = 0, 100

# Одна строка CSV: фамилия, имя, факультет, курс, оценка.
Row = tuple[str, str, str, str, int]


class StudentRepository:
    '''Операции INSERT и SELECT над таблицей Student.'''

    def __init__(self, session: Session) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # INSERT
    # ------------------------------------------------------------------

    def insert_student(
        self,
        last_name: str,
        first_name: str,
        faculty: str,
        course: str,
        grade: int,
    ) -> Student:
        '''Вставить одну запись и вернуть её с присвоенным id.'''
        student = Student(
            last_name=last_name,
            first_name=first_name,
            faculty=faculty,
            course=course,
            grade=grade,
        )
        self._session.add(student)
        self._session.commit()
        return student

    def insert_students(self, rows: Iterable[Row]) -> int:
        '''Вставить пакет записей одной транзакцией; вернуть их число.'''
        students = [
            Student(
                last_name=last_name,
                first_name=first_name,
                faculty=faculty,
                course=course,
                grade=grade,
            )
            for last_name, first_name, faculty, course, grade in rows
        ]
        self._session.add_all(students)
        self._session.commit()
        return len(students)

    # ------------------------------------------------------------------
    # SELECT
    # ------------------------------------------------------------------

    def get_student(self, student_id: int) -> Student | None:
        '''Получить запись по id (или None, если её нет).'''
        return self._session.get(Student, student_id)

    # ------------------------------------------------------------------
    # Заполнение из CSV
    # ------------------------------------------------------------------

    def load_from_csv(self, csv_path: Path) -> int:
        '''
        Заполнить таблицу данными из CSV-файла.

        Все строки вставляются одной транзакцией; возвращает
        количество записанных записей.
        '''
        rows = self._read_csv(csv_path)
        count = self.insert_students(rows)
        logger.info('вставлено записей из %s: %d', csv_path.name, count)
        return count

    # ------------------------------------------------------------------
    # Запросы
    # ------------------------------------------------------------------

    def students_by_faculty(self, faculty: str) -> list[Student]:
        '''Все записи студентов заданного факультета.'''
        stmt = (
            select(Student)
            .where(Student.faculty == faculty)
            .order_by(Student.last_name, Student.first_name, Student.course)
        )
        return list(self._session.scalars(stmt))

    def unique_courses(self) -> list[str]:
        '''Список уникальных названий курсов, по алфавиту.'''
        stmt = select(Student.course).distinct().order_by(Student.course)
        return list(self._session.scalars(stmt))

    def low_grade_students(
        self,
        course: str,
        max_grade: int = 30,
    ) -> list[Student]:
        '''
        Студенты выбранного курса с оценкой ниже ``max_grade``
        баллов, по возрастанию оценки.
        '''
        stmt = (
            select(Student)
            .where(Student.course == course, Student.grade < max_grade)
            .order_by(Student.grade)
        )
        return list(self._session.scalars(stmt))

    def average_grade_by_faculty(self, faculty: str) -> float | None:
        '''
        Средний балл по факультету.

        Возвращает None, если записей этого факультета нет.
        '''
        stmt = select(func.avg(Student.grade)).where(
            Student.faculty == faculty
        )
        value = self._session.scalar(stmt)
        return None if value is None else round(float(value), 2)

    # ------------------------------------------------------------------
    # Внутренние помощники
    # ------------------------------------------------------------------

    @staticmethod
    def _read_csv(csv_path: Path) -> list[Row]:
        '''Прочитать CSV-файл, проверив заголовок и каждую строку.'''
        rows: list[Row] = []
        with csv_path.open(newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != EXPECTED_HEADER:
                raise ValueError(
                    f'неожиданный заголовок в {csv_path.name}: '
                    f'{reader.fieldnames}, ожидался {EXPECTED_HEADER}'
                )
            for line, row in enumerate(reader, start=2):
                rows.append(StudentRepository._parse_row(row, line))
        return rows

    @staticmethod
    def _parse_row(row: Mapping[str, str | None], line: int) -> Row:
        '''Превратить одну строку CSV в запись и проверить поля.'''
        last_name = (row.get('Фамилия') or '').strip()
        first_name = (row.get('Имя') or '').strip()
        faculty = (row.get('Факультет') or '').strip()
        course = (row.get('Курс') or '').strip()
        grade_raw = (row.get('Оценка') or '').strip()

        if not all((last_name, first_name, faculty, course)):
            raise ValueError(f'строка {line}: пустое поле')

        try:
            grade = int(grade_raw)
        except ValueError:
            raise ValueError(
                f'строка {line}: оценка {grade_raw!r} не является числом'
            ) from None

        if not GRADE_MIN <= grade <= GRADE_MAX:
            raise ValueError(
                f'строка {line}: оценка {grade} вне диапазона '
                f'{GRADE_MIN}–{GRADE_MAX}'
            )

        return last_name, first_name, faculty, course, grade
