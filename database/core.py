"""Database core functionality."""

import typing

import sqlalchemy as sql
import sqlalchemy.exc as sql_exc
import sqlalchemy.ext.asyncio as async_sql
import sqlalchemy.orm as orm
import tenacity

import database

_engine: async_sql.AsyncEngine | None = None  # global database engine


class DatabaseModel(orm.DeclarativeBase, async_sql.AsyncAttrs):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    """The model's unique ID."""
    engine: async_sql.AsyncEngine | None = None
    """The database of the model. Defaults to the global database."""

    @property
    def _loading_statement(self):
        """The statement used to load the model from the database."""
        return (
            sql.select(type(self))
            .where((type(self).id == self.id))
            .options(orm.selectinload("*"))
        )

    def __init__(
        self, engine: async_sql.AsyncEngine | None = None, **kwargs: typing.Any
    ):
        super().__init__()
        self.engine = engine
        # set attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

    async def load(self):
        """Load the model instance from the database if it exists."""
        try:
            engine = self.engine or await db_engine()
            statement = self._loading_statement
            async with async_sql.AsyncSession(engine) as session:
                # async with session.begin(): # REVIEW: check if needed
                db_model = await session.scalar(statement)
            self._overwrite(db_model) if db_model else None
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not load model") from e
        return self

    async def save(self):
        """Store the model in the database, overwriting it if it exists."""
        try:
            # use eager loading to prevent errors
            engine = self.engine or await db_engine()
            async with async_sql.AsyncSession(engine) as session:
                async with session.begin():
                    await session.merge(self)
                    await session.commit()
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not save model") from e
        return

    async def delete(self):
        """Delete the model from the database if it exists."""
        try:
            engine = self.engine or await db_engine()
            async with async_sql.AsyncSession(engine) as session:
                async with session.begin():
                    if db_model := await session.get(type(self), self.id):
                        await session.delete(db_model)
                        await session.commit()
        except sql_exc.SQLAlchemyError as e:
            raise DatabaseError("Could not delete model") from e
        return self

    def _overwrite(self, other: typing.Self):
        for field in sql.inspect(type(self)).attrs.keys():
            other_field = getattr(other, field, None)
            setattr(self, field, other_field)
        return self


class DatabaseError(Exception):
    """Exception raised for database errors."""

    pass


async def db_engine():
    """Returns the database engine. If it is not initialized, database
    connection is established and the engine is created.

    Raises:
        ConnectionError: If connection to database could not be established.
    """
    global _engine

    # start database if no engine is available
    if not _engine:
        _engine = await start_engine(database.url)
    # validate and return engine
    await _validate_connection(_engine)
    return _engine


async def start_engine(url):
    """Start a new database engine."""
    # initialize database
    engine = async_sql.create_async_engine(url)
    await _validate_connection(engine)

    # create database schema
    async with engine.begin() as connection:
        await connection.run_sync(DatabaseModel.metadata.create_all)
    database.logger.info(f"Connected to database: {url}")
    return engine


@tenacity.retry(
    # retry on connection errors
    wait=tenacity.wait_random_exponential(min=0.5, max=1),
    stop=tenacity.stop_after_attempt(5),
    retry=tenacity.retry_if_exception_type(ConnectionError),
    reraise=True,
)
async def _validate_connection(engine: async_sql.AsyncEngine):
    try:  # creating a session to validate connection
        async with async_sql.AsyncSession(engine) as session:
            async with session.begin():
                pass
    except Exception:
        raise ConnectionError("Failed to connect to database")
