'''Сервис оценок студентов: FastAPI + SQLAlchemy + Alembic.'''

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from dependencies import get_repository
from models import Student
from repository import StudentRepository
from schemas import AverageOut, LoadCsvOut, StudentIn, StudentOut

logger = logging.getLogger(__name__)

# Файл с исходными данными для эндпоинта /load-csv.
CSV_PATH = Path(__file__).resolve().parent / 'students.csv'

app = FastAPI(
    title='Оценки студентов',
    description=(
        'Сервис хранения и выборки оценок студентов: '
        'FastAPI, SQLAlchemy и Alembic.'
    ),
    version='1.0.0',
)


@app.exception_handler(SQLAlchemyError)
def handle_sqlalchemy_error(
    request: Request,
    exc: SQLAlchemyError,
) -> JSONResponse:
    '''
    Единая обработка ошибок базы данных для всех эндпоинтов.

    Валидация Pydantic (422) и HTTPException (404) не затрагиваются.
    Транзакция откатится при закрытии сессии в get_db.
    '''
    # exc_info=exc: в обработчике sys.exc_info() пуст (другой поток),
    # исключение нужно передать явно.
    logger.error(
        'ошибка базы данных: %s %s',
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={'detail': 'Ошибка работы с базой данных'},
    )


@app.post(
    '/student',
    response_model=StudentOut,
    status_code=201,
    summary='Добавить запись об оценке студента',
)
def create_student(
    data: StudentIn,
    repository: StudentRepository = Depends(get_repository),
) -> Student:
    '''INSERT: валидация через Pydantic и запись в базу.'''
    return repository.insert_student(
        last_name=data.last_name,
        first_name=data.first_name,
        faculty=data.faculty,
        course=data.course,
        grade=data.grade,
    )


@app.post(
    '/load-csv',
    response_model=LoadCsvOut,
    status_code=201,
    summary='Заполнить базу данными из students.csv',
)
def load_students_csv(
    repository: StudentRepository = Depends(get_repository),
) -> LoadCsvOut:
    '''
    Загрузка students.csv в таблицу (одной транзакцией).

    Повторный вызов добавляет записи снова: дублирует данные.
    '''
    try:
        count = repository.load_from_csv(CSV_PATH)
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail=f'Файл {CSV_PATH.name} не найден',
        ) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f'Некорректные данные в {CSV_PATH.name}: {exc}',
        ) from None
    return LoadCsvOut(file=CSV_PATH.name, loaded=count)


@app.get(
    '/students/{student_id}',
    response_model=StudentOut,
    summary='Получить запись по id',
)
def get_student(
    student_id: int,
    repository: StudentRepository = Depends(get_repository),
) -> Student:
    '''SELECT одной записи по первичному ключу.'''
    student = repository.get_student(student_id)
    if student is None:
        raise HTTPException(
            status_code=404,
            detail=f'Студент с id {student_id} не найден',
        )
    return student


@app.get(
    '/faculties/{faculty}/students',
    response_model=list[StudentOut],
    summary='Студенты по названию факультета',
)
def get_faculty_students(
    faculty: str,
    repository: StudentRepository = Depends(get_repository),
) -> list[Student]:
    '''Все записи студентов заданного факультета.'''
    return repository.students_by_faculty(faculty)


@app.get(
    '/faculties/{faculty}/average',
    response_model=AverageOut,
    summary='Средний балл по факультету',
)
def get_faculty_average(
    faculty: str,
    repository: StudentRepository = Depends(get_repository),
) -> AverageOut:
    '''Средний балл по факультету (404, если факультет пуст).'''
    average = repository.average_grade_by_faculty(faculty)
    if average is None:
        raise HTTPException(
            status_code=404,
            detail=f'Факультет «{faculty}» не найден',
        )
    return AverageOut(faculty=faculty, average=average)


@app.get(
    '/courses',
    response_model=list[str],
    summary='Список уникальных курсов',
)
def get_courses(
    repository: StudentRepository = Depends(get_repository),
) -> list[str]:
    '''Уникальные названия курсов.'''
    return repository.unique_courses()


@app.get(
    '/courses/{course}/low-grades',
    response_model=list[StudentOut],
    summary='Студенты курса с оценкой ниже порога',
)
def get_low_grade_students(
    course: str,
    repository: StudentRepository = Depends(get_repository),
    max_grade: int = Query(30, ge=0, le=100, description='Порог, баллы'),
) -> list[Student]:
    '''
    Студенты выбранного курса
    с оценкой ниже ``max_grade`` баллов (по умолчанию 30).
    '''
    return repository.low_grade_students(course, max_grade)
