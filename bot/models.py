"""Models of Telegram entities."""

import typing

import sqlalchemy as sql
import sqlalchemy.ext.asyncio as async_sql
import sqlalchemy.orm as orm
import telegram
from typing_extensions import override

import chatgpt.core as chatgpt
import database.core as database


class TelegramMessage:
    """Telegram message."""

    def __init__(self, message: telegram.Message):
        """Initialize a text message from a Telegram message."""
        message_user = message.from_user or message.sender_chat or message.chat

        self.id = message.message_id
        """The message ID."""
        self.topic_id: int | None = None
        """The topic ID if any."""
        self.chat = TelegramChat(message.chat)
        """The chat in which the message was sent."""
        self.user = TelegramUser(message_user)
        """The user who sent the message."""
        self.reply: TelegramMessage | None = None
        """The message to which this message is a reply if any."""
        self.telegram_message = message
        """The Telegram message instance."""

        # fill-in the topic if any
        if message.is_topic_message and message.message_thread_id:
            self.topic_id = message.message_thread_id
        # fill-in reply message if any
        if reply := message.reply_to_message:
            self.reply = TextMessage(reply)

    @property
    def chat_id(self) -> str:
        """The chat ID used by the chat model."""
        return f"{self.chat.id}_{self.topic_id or ''}"

    @property
    def metadata(self) -> dict[str, str]:
        """The message metadata."""
        metadata = dict(
            id=str(self.id),
            username=self.user.username,
            reply_id=str(self.reply.id) if self.reply else None,
        )
        metadata = {k: v for k, v in metadata.items() if v is not None}
        return metadata


class TelegramChat:
    """Telegram chat."""

    def __init__(self, chat: telegram.Chat):
        """Initialize a chat from a Telegram chat."""
        self.id = chat.id
        """The chat ID."""
        self.title = chat.title or ""
        """The chat title if any."""
        self.telegram_chat = chat
        """The Telegram chat instance."""
        self._username = chat.username

    @property
    def username(self) -> str:
        """The chat's username. The chat title if no username."""
        return self._username or self.title


class TelegramUser:
    """Telegram user."""

    def __init__(self, user: telegram.User | telegram.Chat):
        """Initialize a user from a Telegram user."""
        self.id = user.id
        """The user ID."""
        self.first_name: str
        """The user first name if any."""
        self.last_name = user.last_name
        """The user last name if any."""
        self.telegram_user = user
        """The Telegram user or chat instance."""
        self._username = user.username

        # fill-in first name
        if isinstance(user, telegram.User):
            self.first_name = user.first_name
        else:  # first name for chats is the title
            self.first_name = TelegramChat(user).title

    @property
    def username(self) -> str:
        """The user's username. The user's fullname if no username."""
        return self._username or self.fullname

    @property
    def fullname(self) -> str:
        """The user's fullname."""
        first_last = f"{self.first_name} {self.last_name or ''}"
        return first_last.strip()


class TelegramMetrics(database.DatabaseModel):
    """Telegram metrics."""

    __tablename__ = "telegram_metrics"

    model_id: orm.Mapped[str] = orm.mapped_column(unique=True)
    """The entity's model ID (user, chat, or forum)."""
    usage: orm.Mapped[int] = orm.mapped_column()
    """The entity's token usage count."""
    usage_cost: orm.Mapped[float] = orm.mapped_column()
    """The entity's token usage cost."""
    data: orm.Mapped[str] = orm.mapped_column()
    """Entity related data."""

    def __init__(
        self,
        id: int | None = None,
        model_id: str | None = None,
        usage: int | None = None,
        usage_cost: float | None = None,
        data: str | None = None,
        engine: async_sql.AsyncEngine | None = None,
        **kw: typing.Any,
    ):
        super().__init__(
            id=id,
            model_id=model_id,
            usage=usage,
            usage_cost=usage_cost,
            data=data,
            engine=engine,
            **kw,
        )

    @property
    @override
    def _loading_statement(self):
        return sql.select(type(self)).where(
            (type(self).id == self.id) | (type(self).model_id == self.model_id)
        )


class TextMessage(TelegramMessage):
    """A Telegram text message."""

    def __init__(self, message: telegram.Message):
        super().__init__(message)
        self.text = message.text or message.caption or ""
        """The message text."""

    def to_chat_message(self):
        """Convert the message to a chat model message."""
        return chatgpt.UserMessage(
            self.text, id=self.id, metadata=self.metadata
        )
