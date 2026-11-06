"""Alembic environment for FinView.

The database URL is always taken from DATABASE_URL (loaded from .env), so the
same commands target finview_dev locally and finview_prod on the VPS.
FinView has no ORM models yet, so migrations are written by hand
(no autogenerate).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from backend.db import get_database_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(get_database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
