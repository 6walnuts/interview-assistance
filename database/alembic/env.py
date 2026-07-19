"""Alembic environment. DATABASE_URL comes from the environment, never the ini.

Generate a migration:
  cd database/alembic && DATABASE_URL=postgresql://... alembic revision --autogenerate -m "init"
Apply:
  cd database/alembic && DATABASE_URL=postgresql://... alembic upgrade head
"""
import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "api"))

from app.db import Base  # noqa: E402
from app import models  # noqa: E402,F401  (registers all tables on Base)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=os.environ["DATABASE_URL"], target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
