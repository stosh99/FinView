"""Shared database configuration for the FinView API, loader and migrations."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    """Return DATABASE_URL, failing loudly instead of guessing a database."""
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and point it at "
            "finview_dev (local) or finview_prod (VPS)."
        )
    if url.startswith(("postgresql://", "postgresql+psycopg2://")):
        raise RuntimeError(
            "DATABASE_URL must use the psycopg 3 driver: postgresql+psycopg://..."
        )
    return url


def make_engine() -> Engine:
    return create_engine(get_database_url(), pool_pre_ping=True)
