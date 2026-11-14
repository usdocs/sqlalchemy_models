# Оценки студентов (FastAPI + SQLAlchemy + Alembic)

Сервис оценок студентов на **FastAPI + SQLAlchemy + Alembic**:
модель данных для таблицы из `students.csv`, класс для операций
INSERT и SELECT, загрузка данных из CSV, веб-эндпоинты
и миграции схемы базы.

## Модель данных

Таблица `students` — одна строка, это оценка студента
по одному курсу. У одного студента может быть несколько
записей (по одной на каждый курс).

| Колонка      | Тип      | Описание             |
| ------------ | -------- | -------------------- |
| `id`         | INTEGER  | первичный ключ       |
| `last_name`  | TEXT     | фамилия              |
| `first_name` | TEXT     | имя                  |
| `faculty`    | TEXT     | факультет            |
| `course`     | TEXT     | курс                 |
| `grade`      | INTEGER  | оценка, 0–100 баллов |

База — файл `students.db` (SQLite) рядом с проектом,
создаётся **только миграциями Alembic** и не попадает в git
(см. `.gitignore`).

## Структура проекта

```
sqlalchemy_models/
├── main.py          # приложение FastAPI и эндпоинты
├── models.py        # SQLAlchemy-модель Student
├── schemas.py       # Pydantic-модели запросов и ответов
├── dependencies.py  # зависимости FastAPI: get_db, get_repository
├── database.py      # движок и фабрика сессий
├── repository.py    # StudentRepository: INSERT/SELECT и запросы
├── alembic/         # миграции (env.py, versions/)
├── alembic.ini      # конфигурация Alembic
├── pyproject.toml   # зависимости (управляются через uv)
├── students.csv     # исходные данные
└── README.md
```

## Установка и запуск (через uv)

```bash
uv sync                      # создать .venv и установить зависимости

uv run alembic upgrade head  # создать таблицы миграцией
uv run uvicorn main:app --reload   # запустить сервис
```

База заполняется запросом к эндпоинту `POST /load-csv`
(см. ниже).

- API: http://127.0.0.1:8000
- Интерактивная документация (Swagger): http://127.0.0.1:8000/docs

При изменении `models.py` новая миграция создаётся командой:

```bash
uv run alembic revision --autogenerate -m 'описание изменения'
uv run alembic upgrade head
```

## Эндпоинты

| Метод | Путь                          | Описание                              |
| ----- | ----------------------------- | ------------------------------------- |
| `POST` | `/student`                   | Добавить запись (INSERT)              |
| `POST` | `/load-csv`                  | Заполнить базу из `students.csv`      |
| `GET`  | `/students/{student_id}`     | Запись по id (SELECT)                 |
| `GET`  | `/faculties/{faculty}/students` | Студенты по названию факультета    |
| `GET`  | `/faculties/{faculty}/average`  | Средний балл по факультету          |
| `GET`  | `/courses`                   | Список уникальных курсов              |
| `GET`  | `/courses/{course}/low-grades` | Студенты курса с оценкой ниже порога (`max_grade`, по умолчанию 30) |

### Пример: добавление записи

```bash
curl -s -X POST http://127.0.0.1:8000/student \
  -H "Content-Type: application/json" \
  -d '{
    "last_name": "Иванов",
    "first_name": "Иван",
    "faculty": "ФТФ",
    "course": "Физика",
    "grade": 85
  }'
```

Ответ — `201 Created` с сохранённой записью:

```json
{"id": 216, "last_name": "Иванов", "first_name": "Иван",
 "faculty": "ФТФ", "course": "Физика", "grade": 85}
```

### Пример: загрузка из CSV

```bash
curl -s -X POST http://127.0.0.1:8000/load-csv
```

Ответ — `201 Created`:

```json
{"file": "students.csv", "loaded": 215}
```

Запись добавляется в таблицу, поэтому повторный вызов
дублирует данные. Ошибки файла (отсутствует, некорректная
строка) возвращают `500` с описанием.

### Пример: выборки

```bash
curl -s "http://127.0.0.1:8000/courses"
# ["Информатика", "История", "Мат. Анализ", "Психология", "Теор. Механика", "Физика"]

curl -s "http://127.0.0.1:8000/faculties/ФТФ/average"
# {"faculty": "ФТФ", "average": 49.73}

curl -s "http://127.0.0.1:8000/courses/Мат.%20Анализ/low-grades"
# 13 студентов «Мат. Анализ» с оценкой ниже 30,
# отсортировано по возрастанию оценки
```

## Валидация

- **Фамилия и имя** — с заглавной буквы, только буквы кириллицы:
  `^А-ЯЁ[а-яё]+$`;
- **Оценка** — целое число от 0 до 100;
- **Факультет и курс** — непустые строки.

Невалидные данные отклоняются с кодом `422 Unprocessable Entity`.
Несуществующие сущности (`/students/{id}`, средний балл по пустому
факультету) отклоняются с кодом `404 Not Found`.
Ошибки записи в базу (например, `database is locked`) перехватываются
и возвращают `500 Internal Server Error` с сообщением
«Не удалось сохранить запись в базу данных»; транзакция при этом
откатывается, частичных данных не остаётся.

Загрузка из CSV дополнительно проверяет заголовок файла и каждую
строку (пустые поля, оценка — целое число 0–100); при ошибке
`POST /load-csv` возвращает `500` с сообщением о номере строки,
и ни одна невалидная запись не попадает в базу.

## Как это устроено

- `models.py` — ORM-модель `Student` на базе `DeclarativeBase`
  (SQLAlchemy 2.0, типизированные колонки `Mapped[...]`);
- `alembic/` — миграции схемы: `env.py` берёт строку подключения
  из `database.py` и метаданные из `Base.metadata`, файл
  `versions/…_create_students_table.py` создаёт таблицу;
- `database.py` — движок SQLite, фабрика сессий `SessionLocal`
  (с `expire_on_commit=False`);
- `dependencies.py` — зависимости FastAPI: `get_db()` — сессия
  на время одного запроса, `get_repository()` — репозиторий
  поверх этой сессии;
- `repository.py` — класс `StudentRepository` (принимает сессию)
  с операциями INSERT (`insert_student`, `insert_students`)
  и SELECT (`get_student`), загрузкой из CSV (`load_from_csv`)
  и запросами:
  - `students_by_faculty` — студенты по названию факультета;
  - `unique_courses` — список уникальных курсов;
  - `low_grade_students` — студенты выбранного курса
    с оценкой ниже 30 баллов;
  - `average_grade_by_faculty` — средний балл по факультету;
- `schemas.py` — Pydantic-модели: `StudentIn` (валидация ввода),
  `StudentOut` (ответ из ORM), `AverageOut` (средний балл).
