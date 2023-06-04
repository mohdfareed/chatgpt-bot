"""Database core functionality. It is responsible for managing the database
and its connection. It also provides the base model class for the database
models, which defines core functionality shared by all models."""

import os

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
    __abstract__ = True

    @property
    def primary_keys(self) -> tuple:
        """The values of the primary keys of the model."""
        inspector = sql.inspect(type(self))
        key_names = [key.name for key in inspector.primary_key]
        return tuple(getattr(self, attr) for attr in key_names)

    def load(self):
        """Load the model from the database. Overwrites the current instance
        only if it exists in the database."""
        with orm.Session(engine()) as session:
            db_instance = session.get(self.__class__, self.primary_keys)
            self.overwrite(db_instance) if db_instance else None
        return self

    def save(self):
        """Store the model in the database. Overwrites the current instance
        with the new database instance."""
        with orm.Session(engine()) as session:
            db_instance = session.merge(self)
            session.commit()
            self.overwrite(db_instance)
        return self

    def delete(self):
        """Delete the model from the database if it exists."""
        with orm.Session(engine()) as session:
            if db_obj := session.get(self.__class__, self.primary_keys):
                session.delete(db_obj)
                session.commit()
        return self

    def overwrite(self, other: "DatabaseModel"):
        """Overwrites the current instance with another instance."""
        for field in sql.inspect(type(self)).attrs.keys():
            other_field = getattr(other, field)
            setattr(self, field, other_field)
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
