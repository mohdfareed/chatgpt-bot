"""Database core functionality. It is responsible for managing the database
and its connection. It also provides the base model class for the database
models, which defines core functionality shared by all models."""

import os
import typing

import sqlalchemy as sql
import sqlalchemy.orm as orm
import tenacity

from database import logger

# default to sqlite database
_db_path = os.path.abspath(os.path.dirname(__file__))
_default_url = f"sqlite:///{_db_path}/database.db"
_engine: sql.Engine | None = None  # global database engine

url = os.environ.get("DATABASE_URL") or _default_url
"""The database URL."""


class DatabaseModel(orm.DeclarativeBase):
    @property
    def primary_keys(self) -> tuple:
        # return a tuple of the model's primary keys
        inspector = sql.inspect(type(self))
        key_names = [key.name for key in inspector.primary_key]
        return tuple(getattr(self, attr) for attr in key_names)

    def save(self):
        """Store the model in the database. Merge if it already exists."""

        with orm.Session(engine()) as session:
            session.merge(self)
            session.commit()
        return self

    def delete(self):
        """Delete the model from the database."""

        with orm.Session(engine()) as session:
            session.delete(self)
            session.commit()
        return self

    def load(self) -> typing.Self:
        """Load the model from the database. It has no effect if the model
        doesn't exist in the database. Returns the loaded model."""

        with orm.Session(engine()) as session:
            if db_instance := session.get(
                self.__class__,
                self.primary_keys,
                options=[orm.selectinload("*")],
            ):
                self = db_instance
        return self


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
        orm.Session(engine).close()
    except Exception:
        raise ConnectionError("Failed to connect to database")


def _start_engine():
    # initialize database
    logger.info("Initializing database...")
    engine = sql.create_engine(url)
    _validate_connection(engine)
    # create database schema
    DatabaseModel.metadata.create_all(engine)
    logger.info(f"Connected to database: {url}")
    return engine
