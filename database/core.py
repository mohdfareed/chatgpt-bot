"""Database core functionality. It is responsible for managing the database
within a Docker container."""

import tenacity as _tenacity
from sqlalchemy import Engine as _Engine
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session as _Session

from database import logger as _logger
from database import url as _db_url
from database.models import metadata as _db_metadata

engine: _Engine
"""The database engine."""


def start() -> None:
    """Initialize the database in a Docker container."""
    global engine

    # initialize database
    _logger.info("Initializing database...")
    engine = _create_engine(_db_url)
    validate_connection()
    # initialize tables
    _db_metadata.create_all(engine)


@_tenacity.retry(
    # retry on connection errors
    wait=_tenacity.wait_fixed(1),  # retry every second
    stop=_tenacity.stop_after_attempt(5),  # for 5 seconds
    retry=_tenacity.retry_if_exception_type(ConnectionError),
    reraise=True,
)
def validate_connection() -> None:
    """Check if the database is connected.

    Raises:
        ConnectionError: If the database is not connected.
    """
    global engine

    try:  # check connection to database
        engine.connect()
        _Session(engine).close()
    except Exception:
        raise ConnectionError("Failed to connect to database")
