"""Database core functionality. It is responsible for managing the database
and its connection."""

import logging
import os

import tenacity
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

# default to sqlite database
_db_path = os.path.abspath(os.path.dirname(__file__))
_default_url = f"sqlite:///{_db_path}/database.db"
_engine: Engine | None = None  # global database engine

logger = logging.getLogger(__name__)
"""The database logger."""
url = os.environ.get("DATABASE_URL") or _default_url
"""The database URL."""


def engine():
    """Returns the database engine. If it is not initialized, database
    connection is established and the engine is created.

    Raises:
        ConnectionError: If connection to database could not be established.
    """
    global _engine

    # start database if no engine is available
    if not _engine:
        _engine = _start_engine()
    # validate and return engine
    _validate_connection(_engine)
    return _engine


@tenacity.retry(
    # retry on connection errors
    wait=tenacity.wait_random_exponential(min=0.5, max=1),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type(ConnectionError),
    reraise=True,
)
def _validate_connection(engine):
    try:  # creating a session to validate connection
        Session(engine).close()
    except Exception:
        raise ConnectionError("Failed to connect to database")


def _start_engine():
    from .db_model import DatabaseModel

    # initialize database
    logger.info("Initializing database...")
    engine = create_engine(url)
    _validate_connection(engine)
    # create database schema
    DatabaseModel.metadata.create_all(engine)
    logger.info(f"Connected to database: {url}")
    return engine
