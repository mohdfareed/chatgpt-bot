"""The database models defining the database schema."""


import sqlalchemy as sql
import sqlalchemy.orm as orm

from chatgpt.langchain.prompts import ASSISTANT_PROMPT
from database.core import DatabaseModel


class User(DatabaseModel):
    """A telegram user."""

    __tablename__ = "users"

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    """The user's unique ID."""
    token_usage: orm.Mapped[int] = orm.mapped_column()
    """The user's cumulative token usage."""
    usage: orm.Mapped[float] = orm.mapped_column()
    """The user's cumulative usage in USD."""

    def __init__(self, id: int, token_usage: int = 0, usage: float = 0):
        self.id = id
        self.token_usage = token_usage
        self.usage = usage


class ChatGPT(DatabaseModel):
    """A ChatGPT model's parameters. Self-destructs when not in use."""

    __tablename__ = "models"

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, autoincrement=True
    )
    """The model's unique ID. It is automatically generated."""
    prompt: orm.Mapped[str] = orm.mapped_column()
    """The model's system prompt."""

    def __init__(self, id: int | None = None, prompt: str = ASSISTANT_PROMPT):
        self.id = id or self.id
        self.prompt = prompt


class Chat(DatabaseModel):
    """A telegram private chat (user), group chat, forum, or channel."""

    __tablename__ = "chats"

    _topic_id: orm.Mapped[int] = orm.mapped_column(
        "topic_id", primary_key=True, default=-1
    )
    _model: orm.Mapped[ChatGPT | None] = orm.relationship()
    _model_key = sql.ForeignKey(ChatGPT.id)

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    """The chat's unique ID."""
    model_id: orm.Mapped[int | None] = orm.mapped_column(_model_key)
    """The chat's active ChatGPT model ID if any."""
    token_usage: orm.Mapped[int] = orm.mapped_column()
    """The chat's cumulative token usage."""
    usage: orm.Mapped[float] = orm.mapped_column()
    """The chat's cumulative usage in USD."""

    @property
    def topic_id(self):
        """The chat's topic ID if any."""
        return self._topic_id if self._topic_id != -1 else None

    @topic_id.setter
    def topic_id(self, value: int | None):
        # only allow positive topic IDs or None, internally store -1 for None
        if value is not None and value < 0:
            raise ValueError("Topic ID must be >= 0")
        self._topic_id = value if value is not None else -1

    @property
    def model(self):
        """The chat's active ChatGPT model if any. Created on demand."""
        self._model = self._model or ChatGPT()
        return self._model

    @model.setter
    def model(self, value: ChatGPT | None):
        self._model = value

    @property
    def primary_keys(self):
        # define primary keys due to changed primary key name
        return (self.id, self._topic_id)

    def __init__(
        self,
        id: int,
        topic_id: int | None = None,
        token_usage: int = 0,
        usage: float = 0,
    ):
        self.model = ChatGPT()
        self.id = id
        self.topic_id = topic_id
        self.token_usage = token_usage
        self.usage = usage

    # define the primary keys order
    __table_args__ = (sql.PrimaryKeyConstraint(id, _topic_id),)
