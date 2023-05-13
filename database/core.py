"""Database core functionality. It is responsible for managing the database
within a Docker container."""

import tenacity
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from database import URL, logger
from database.models import Base

engine: Engine
"""The database engine."""


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


@tenacity.retry(
    # retry every second for 5 seconds on connection errors
    wait=tenacity.wait_fixed(1),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type(ConnectionError),
    reraise=True
)
def validate_connection() -> None:
    """Check if the database is connected.

    Raises:
        ConnectionError: If the database is not connected.
    """
    global engine

    try:  # check connection to database
        engine.connect()
        Session(engine).close()
    except Exception:
        raise ConnectionError("failed to connect to database")
