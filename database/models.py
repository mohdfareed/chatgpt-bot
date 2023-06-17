"""The database models defining the database schema."""

import typing

import sqlalchemy as sql
import sqlalchemy.orm as orm
import sqlalchemy_utils
from sqlalchemy_utils.types.encrypted import encrypted_type

import database

_encrypted = sqlalchemy_utils.StringEncryptedType(
    sql.Unicode, database.encryption_key, encrypted_type.FernetEngine
)


class User(database.core.DatabaseModel):
    """A telegram user."""

    __tablename__ = "users"

    token_usage: orm.Mapped[int] = orm.mapped_column(default=0)
    """The user's cumulative token usage."""
    usage: orm.Mapped[float] = orm.mapped_column(default=0)
    """The user's cumulative usage in USD."""

    def __init__(self, id: int, **kw: typing.Any):
        super().__init__(id=id, **kw)


class Message(database.core.DatabaseModel):
    """A message in a chat history."""

    __tablename__ = "messages"

    session_id: orm.Mapped[str] = orm.mapped_column()
    """The session to which the message belongs."""
    content: orm.Mapped[str] = orm.mapped_column(_encrypted)
    """The message's contents."""

    def __init__(self, session_id: str, **kw: typing.Any):
        super().__init__(session_id=session_id, **kw)

    @classmethod
    def load_messages(cls, session_id: str):
        """Load a chat history by its session ID."""

        statement = sql.select(cls).where(cls.session_id == session_id)
        with orm.Session(database.core.engine()) as session:
            return session.scalars(statement).all()


class ChatModel(database.core.DatabaseModel):
    """A ChatGPT model's parameters."""

    __tablename__ = "models"

    session_id: orm.Mapped[str] = orm.mapped_column(unique=True)
    """The unique session to which the model belongs."""
    parameters: orm.Mapped[str] = orm.mapped_column(_encrypted)
    """The model's parameters."""

    def __init__(self, session_id: str, **kw: typing.Any):
        super().__init__(session_id=session_id, **kw)

    def _loading_statement(self):
        # load a model by its ID or session ID
        return sql.select(ChatModel).where(
            (ChatModel.id == self.id)
            | (ChatModel.session_id == self.session_id)
        )


class Chat(database.core.DatabaseModel):
    """A telegram private chat (user), group chat, forum, or channel."""

    __tablename__ = "chats"

    topic_id: orm.Mapped[int | None] = orm.mapped_column()
    """The chat's topic ID. None for a general chat."""
    token_usage: orm.Mapped[int] = orm.mapped_column()
    """The chat's cumulative token usage."""
    usage: orm.Mapped[float] = orm.mapped_column()
    """The chat's cumulative usage in USD."""

    @property
    def session_id(self):
        """The chat's session ID."""
        return f"{self.id}:{self.topic_id}"

    def __init__(self, id: int, topic_id: int | None = None, **kw: typing.Any):
        super().__init__(id=id, topic_id=topic_id, **kw)
