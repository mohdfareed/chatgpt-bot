"""Database core functionality. It is responsible for managing the database
within a Docker container."""

import tenacity
import logging
from sqlalchemy import Engine
from sqlalchemy_utils import database_exists

from database import logger

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
    from sqlalchemy import create_engine

    from database import URL
    from database.models import Base
    global engine

    # initialize database
    logger.info("initializing database...")
    engine = create_engine(URL)
    while not database_exists(URL):
        raise ConnectionError("failed to connect to database")

    # initialize tables
    Base.metadata.create_all(engine)


def stop() -> None:
    """Backup and stop the database engine and container."""
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

    # check connection to database
    if not database_exists(engine.url):
        raise ConnectionError("failed to connect to database")
