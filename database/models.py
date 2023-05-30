"""The models defining the database schema."""

import sqlalchemy as _sql
from chatgpt.langchain import prompts as _prompts
from sqlalchemy import orm as _orm

from database import core as _db_core


class _Base(_orm.DeclarativeBase):
    id: _orm.Mapped[int] = _orm.mapped_column(primary_key=True)
    """The database model's unique ID."""

    @classmethod
    def get(cls, *keys):
        """Get a database model by its primary keys."""

        _db_core.validate_connection()
        with _orm.Session(_db_core.engine) as session:
            return session.get(cls, keys)

    def store(self) -> None:
        """Store the model in the database. Merge if it already exists."""

        _db_core.validate_connection()
        with _orm.Session(_db_core.engine) as session:
            session.merge(self)
            session.commit()

    def delete(self) -> None:
        """Delete the model from the database."""

        _db_core.validate_connection()
        with _orm.Session(_db_core.engine) as session:
            session.delete(self)
            session.commit()


class Model(_Base):
    """A ChatGPT model's parameters."""

    __tablename__ = "models"

    chats: _orm.Mapped[list["Chat"]] = _orm.relationship(
        back_populates="model"
    )
    """The chats using the model."""
    prompt: _orm.Mapped[str] = _orm.mapped_column(
        default=_prompts.ASSISTANT_PROMPT
    )
    """The model's system prompt."""

    @classmethod
    def get(cls, id: int) -> "Model":
        return super().get(id) or cls(id=id)


class User(_Base):
    """A telegram user."""

    __tablename__ = "users"

    token_usage: _orm.Mapped[int] = _orm.mapped_column(default=0)
    """The user's cumulative token usage."""
    usage: _orm.Mapped[float] = _orm.mapped_column(default=0)
    """The user's cumulative usage in USD."""

    def __init__(self, id: int, token_usage: int = 0, usage: float = 0):
        self.id = id
        self.token_usage = token_usage
        self.usage = usage

    @classmethod
    def get(cls, id: int) -> "User":
        return super().get(id) or cls(id=id)


class Chat(_Base):
    """A telegram private chat (user), group chat, forum, or channel."""

    __tablename__ = "chats"

    topic_id: _orm.Mapped[int | None] = _orm.mapped_column(
        primary_key=True, nullable=True
    )
    """The chat's topic ID if any."""

    model_id: _orm.Mapped[int | None] = _orm.mapped_column(
        _sql.ForeignKey(Model.id)
    )
    """The chat's ChatGPT model ID if any."""
    model: _orm.Mapped[Model | None] = _orm.relationship(
        back_populates="chats"
    )
    """The chat's ChatGPT model."""

    token_usage: _orm.Mapped[int] = _orm.mapped_column(default=0)
    """The chat's cumulative token usage."""
    usage: _orm.Mapped[float] = _orm.mapped_column(default=0.0)
    """The chat's cumulative usage in USD."""

    @classmethod
    def get(cls, id: int, topic_id: int | None = None) -> "Chat":
        return super().get(id, topic_id) or cls(id=id, topic_id=topic_id)

    def set_model(self, model: Model, prune: bool = False) -> None:
        """Set the chat's ChatGPT model.

        Args:
            model: The new model.
            prune: Delete the old model if it is not used by any chat.
        """

        if self.model:  # disconnect from old model
            self.model.chats.remove(self)
            # delete model if no other chats use it
            if prune and not self.model.chats:
                self.model.delete()
        # set new model
        self.model = model
        self.store()

    __table_args__ = (_sql.PrimaryKeyConstraint("id", "topic_id"),)


metadata = _Base.metadata
"""The database schema metadata."""
