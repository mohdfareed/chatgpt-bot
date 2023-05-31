"""The models defining the database schema."""


from chatgpt.langchain import prompts
from sqlalchemy import ForeignKey, orm

from .db_model import DatabaseModel


class Model(DatabaseModel):
    """A ChatGPT model's parameters."""

    __tablename__ = "models"

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, autoincrement=True
    )
    """The model's unique ID. It is automatically generated."""

    prompt: orm.Mapped[str] = orm.mapped_column()
    """The model's system prompt."""
    chats: orm.Mapped[list["Chat"]] = orm.relationship(back_populates="model")
    """The chats using the model."""

    def __init__(self, id: int | None, prompt: str = prompts.ASSISTANT_PROMPT):
        self.id = id or self.id
        self.prompt = prompt

    def detach(self, chat: "Chat"):
        """Detach the model from a chat. Delete the model no chats are using
        it."""

        self.chats.remove(chat)
        self.save() if self.chats else self.delete()


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


class Chat(DatabaseModel):
    """A telegram private chat (user), group chat, forum, or channel."""

    __tablename__ = "chats"
    _topic_id: orm.Mapped[int] = orm.mapped_column(
        "topic_id", primary_key=True, default=-1
    )

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    """The chat's unique ID."""

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

    token_usage: orm.Mapped[int] = orm.mapped_column()
    """The chat's cumulative token usage."""
    usage: orm.Mapped[float] = orm.mapped_column()
    """The chat's cumulative usage in USD."""

    model_id: orm.Mapped[int | None] = orm.mapped_column(ForeignKey(Model.id))
    """The chat's ChatGPT model ID if any."""
    model: orm.Mapped[Model | None] = orm.relationship(back_populates="chats")
    """The chat's ChatGPT model."""

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

    def set_model(self, model: Model) -> None:
        """Set the chat's ChatGPT model."""

        # detach from old model
        self.load()
        self.model.detach(self) if self.model else None
        # set new model
        self.model = model
        self.save()
