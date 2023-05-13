"""Database core functionality. It is responsible for managing the database
within a Docker container."""

import logging

import tenacity
from sqlalchemy import Engine, create_engine
from sqlalchemy_utils import database_exists

from database import URL, logger
from database.models import Base

_retry_on_db_error = tenacity.retry(
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type(ConnectionError),
    before_sleep=tenacity.before_sleep_log(logger, logging.INFO),
    reraise=True
)

engine: Engine
"""The database engine."""


@_retry_on_db_error
def start() -> None:
    """Initialize the database in a Docker container."""
    global engine

    # initialize database
    logger.info("initializing database...")
    engine = create_engine(URL)
    validate_connection()
    # initialize tables
    Base.metadata.create_all(engine)


def stop() -> None:
    """Stop the database engine."""
    global engine

    engine.dispose() if engine else None
    logger.info("database has stopped")


@_retry_on_db_error
def validate_connection() -> None:
    """Check if the database is connected.

    Raises:
        ConnectionError: If the database is not connected.
    """
    global engine

    try:  # check connection to database
        engine.connect()
    except Exception:
        raise ConnectionError("failed to connect to database")
