"""The database models defining the database schema."""


from chatgpt.langchain.prompts import ASSISTANT_PROMPT
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.core import DatabaseModel


class Model(DatabaseModel):
    """A ChatGPT model's parameters. Self-destructs when not in use."""

    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    """The model's unique ID. It is automatically generated."""
    prompt: Mapped[str] = mapped_column()
    """The model's system prompt."""
    chats: Mapped[list["Chat"]] = relationship(back_populates="_model")
    """The chats using the model."""

    def __init__(self, id: int | None = None, prompt: str = ASSISTANT_PROMPT):
        self.id = id or self.id
        self.prompt = prompt

    def detach(self, chat: "Chat"):
        """Detach the model from a chat. Delete the model when no chats are
        using it."""

        self.chats.remove(chat)
        self.save() if self.chats else self.delete()


class User(DatabaseModel):
    """A telegram user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    """The user's unique ID."""
    token_usage: Mapped[int] = mapped_column()
    """The user's cumulative token usage."""
    usage: Mapped[float] = mapped_column()
    """The user's cumulative usage in USD."""

    def __init__(self, id: int, token_usage: int = 0, usage: float = 0):
        self.id = id
        self.token_usage = token_usage
        self.usage = usage


class Chat(DatabaseModel):
    """A telegram private chat (user), group chat, forum, or channel."""

    __tablename__ = "chats"

    _model: Mapped[Model | None] = relationship(back_populates="chats")
    _topic_id: Mapped[int] = mapped_column(
        "topic_id", primary_key=True, default=-1
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    """The chat's unique ID."""
    model_id: Mapped[int | None] = mapped_column(ForeignKey(Model.id))
    """The chat's ChatGPT model ID if any."""
    token_usage: Mapped[int] = mapped_column()
    """The chat's cumulative token usage."""
    usage: Mapped[float] = mapped_column()
    """The chat's cumulative usage in USD."""

    @property
    def topic_id(self):
        """The chat's topic ID if any."""
        return self._topic_id if self._topic_id != -1 else None

    @topic_id.setter
    def topic_id(self, value: int | None):
        # only allow positive topic IDs or None
        # internally store -1 for None
        if value is not None and value < 0:
            raise ValueError("Topic ID must be >= 0")
        self._topic_id = value if value is not None else -1

    @property
    def model(self):
        """The chat's ChatGPT model if any. Created on demand."""
        self._model = self._model or Model()
        return self._model

    @model.setter
    def model(self, value: Model):
        # detach old model and attach new one
        self._model.detach(self) if self._model else None
        self._model = value

    def __init__(
        self,
        id: int,
        topic_id: int | None = None,
        token_usage: int = 0,
        usage: float = 0,
    ):
        self.id = id
        self.topic_id = topic_id
        self.token_usage = token_usage
        self.usage = usage

    @property
    def primary_keys(self):
        # define primary keys due to changed primary key name
        return (self.id, self._topic_id)

    # define the primary keys order
    __table_args__ = (PrimaryKeyConstraint(id, _topic_id),)
