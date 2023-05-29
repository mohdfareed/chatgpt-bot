"""The models defining the database schema."""

from typing import Type as _Type
from typing import TypeVar as _TypeVar

from sqlalchemy import orm as _orm

from database import core as _db_core

T = _TypeVar("T", bound="_BaseModel")
"""Database model generic type variable."""


class _BaseModel(_orm.DeclarativeBase):
    """The base class for all database models."""

    id: _orm.Mapped[int] = _orm.mapped_column(primary_key=True)
    """The model's unique ID."""

    def __init__(self, id: int, **kw):
        super().__init__(**kw)
        self.id = id

    @classmethod
    def get(cls: _Type[T], *keys) -> T:
        """Get a model by its primary keys."""

        _db_core.validate_connection()
        with _orm.Session(_db_core.engine) as session:
            return session.get(cls, keys) or cls(*keys)

    def store(self) -> None:
        """Store the model in the database. Merge if it already exists."""

        _db_core.validate_connection()
        with _orm.Session(_db_core.engine) as session:
            session.merge(self)
            session.commit()


class Chat(_BaseModel):
    """A telegram private chat (user), group chat, or channel."""

    __tablename__ = "chats"

    topic_id: _orm.Mapped[int | None] = _orm.mapped_column(primary_key=True)
    """The chat's topic ID if any."""
    usage: _orm.Mapped[int] = _orm.mapped_column(default=0)
    """The chat's cumulative token usage."""

    def __init__(self, id: int, topic_id: int | None = None, usage: int = 0):
        super().__init__(id)
        self.topic_id = topic_id
        self.usage = usage

    @classmethod
    def get(cls: _Type[T], id: int, topic_id: int | None = None) -> T:
        return super().get((id, topic_id))


class User(_BaseModel):
    """A telegram user."""

    __tablename__ = "users"

    usage: _orm.Mapped[int] = _orm.mapped_column(default=0)
    """The user's cumulative token usage."""

    def __init__(self, id: int, usage: int = 0):
        super().__init__(id)
        self.usage = usage

    @classmethod
    def get(cls: _Type[T], id: int) -> T:
        return super().get(id)


metadata = _BaseModel.metadata
"""The database schema metadata."""
