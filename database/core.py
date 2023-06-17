"""Database core functionality."""

import typing

import sqlalchemy as sql
import sqlalchemy.exc as sql_exc
import sqlalchemy.orm as orm
import tenacity

import database

_engine: sql.Engine | None = None  # global database engine


class DatabaseModel(orm.DeclarativeBase):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    """The model's unique ID."""

    def load(self):
        """Load the model instance from the database if it exists."""
        try:
            with orm.Session(engine()) as session:
                db_instance = session.query(type(self)).get(self.id)
                self._overwrite(db_instance) if db_instance else None
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not load model") from e
        return self

    def save(self):
        """Store the model in the database, overwriting it if it exists."""
        try:
            with orm.Session(engine()) as session:
                db_instance = session.merge(self)
                session.commit()
                self._overwrite(db_instance)  # load updated instance
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not save model") from e
        return self

    def delete(self):
        """Delete the model from the database if it exists."""
        try:
            with orm.Session(engine()) as session:
                if db_obj := session.get(type(self), self.id):
                    session.delete(db_obj)
                    session.commit()
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not delete model") from e
        return self

    def _overwrite(self, other: typing.Self):
        for field in sql.inspect(type(self)).attrs.keys():
            other_field = getattr(other, field)
            setattr(self, field, other_field)
        return self

    def _loading_statement(self):
        return sql.select(type(self)).where(type(self).id == self.id)


class DatabaseError(Exception):
    """Exception raised for database errors."""


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
    database.logger.info("Initializing database...")
    engine = sql.create_engine(database.url)
    _validate_connection(engine)
    # create database schema
    DatabaseModel.metadata.create_all(engine)
    database.logger.info(f"Connected to database: {database.url}")
    return engine
