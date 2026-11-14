'''Среда выполнения миграций Alembic.'''

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Корень проекта в sys.path, чтобы работали импорты database и models.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import DATABASE_URL  # noqa: E402
from models import Base  # noqa: E402

# Alembic Config: доступ к значениям из alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Строка подключения берётся из database.py, а не из alembic.ini.
config.set_main_option('sqlalchemy.url', DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    '''Миграции в офлайн-режиме: SQL без подключения к базе.'''
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    '''Миграции в онлайн-режиме: через подключение к базе.'''
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
