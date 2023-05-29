"""The models defining the database schema."""

from typing import Type, TypeVar

from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from database import core as db

T = TypeVar("T", bound="Base")
"""A generic type variable for database models."""


class Base(DeclarativeBase):
    """The base class for all database models."""

    id: Mapped[str] = mapped_column(primary_key=True)
    """The model's unique ID."""

    @classmethod
    def get(cls: Type[T], id: int | str) -> T:
        db.validate_connection()
        with Session(db.engine) as session:
            return session.get(cls, id) or cls(id=id)

    def store(self) -> None:
        db.validate_connection()
        with Session(db.engine) as session:
            session.merge(self)
            session.commit()


class Chat(Base):
    """A telegram private chat (user), group chat, or channel."""

    __tablename__ = "chat"

    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    """The chat's cumulative token usage."""

    def __init__(self, id: str, usage: int = 0):
        self.id = id
        self.usage = usage

    def __repr__(self):
        return f"<Chat(id={self.id})>"


class User(Base):
    """A telegram user."""

    __tablename__ = "user"

    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    """The user's cumulative token usage."""

    def __init__(self, id: str, usage: int = 0):
        self.id = id
        self.usage = usage

    def __repr__(self):
        return f"<User(id={self.id})>"
