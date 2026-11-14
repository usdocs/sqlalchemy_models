'''Pydantic-модели входных и выходных данных эндпоинтов.'''

import re

from pydantic import BaseModel, ConfigDict, Field

# Фамилия/имя: заглавная буква кириллицы, дальше — только строчные.
CYRILLIC_NAME_RE = re.compile(r'^[А-ЯЁ][а-яё]+$')


class StudentIn(BaseModel):
    '''Входная модель: новая запись об оценке студента.'''

    last_name: str = Field(
        ...,
        pattern=CYRILLIC_NAME_RE,
        description='Фамилия: с заглавной буквы, только буквы кириллицы',
        examples=['Иванов'],
    )
    first_name: str = Field(
        ...,
        pattern=CYRILLIC_NAME_RE,
        description='Имя: с заглавной буквы, только буквы кириллицы',
        examples=['Иван'],
    )
    faculty: str = Field(
        ...,
        min_length=1,
        description='Факультет',
        examples=['ФТФ'],
    )
    course: str = Field(
        ...,
        min_length=1,
        description='Курс',
        examples=['Мат. Анализ'],
    )
    grade: int = Field(
        ...,
        ge=0,
        le=100,
        description='Оценка, 0–100 баллов',
        examples=[85],
    )


class StudentOut(BaseModel):
    '''Выходная модель: запись таблицы students.'''

    model_config = ConfigDict(from_attributes=True)

    id: int
    last_name: str
    first_name: str
    faculty: str
    course: str
    grade: int


class AverageOut(BaseModel):
    '''Выходная модель: средний балл по факультету.'''

    faculty: str
    average: float


class LoadCsvOut(BaseModel):
    '''Выходная модель: результат загрузки данных из CSV.'''

    file: str
    loaded: int
