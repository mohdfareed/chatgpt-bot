"""The base model of the database. Defines methods and attributes shared by
all models."""

from typing import Any

from sqlalchemy import inspect, orm

from .core import engine


class DatabaseModel(orm.DeclarativeBase):
    def save(self):
        """Store the model in the database. Merge if it already exists."""

        with orm.Session(engine()) as session:
            session.merge(self)
            session.commit()
        return self

    def delete(self) -> None:
        """Delete the model from the database."""

        with orm.Session(engine()) as session:
            session.delete(self)
            session.commit()

    def load(self):
        """Load the model from the database. It has no effect if the model
        doesn't exist in the database. Returns the loaded model."""

        loader = orm.selectinload
        with orm.Session(engine()) as session:
            if db_instance := session.get(
                type(self),
                self.primary_keys(),
                options=[loader("*")],
            ):
                self = db_instance
        return self.save()

    def primary_keys(self) -> tuple[Any, ...]:
        # return a tuple of the model's primary keys
        inspector = inspect(type(self))
        return tuple(column.name for column in inspector.primary_key)
