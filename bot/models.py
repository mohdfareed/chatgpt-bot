"""Models of Telegram entities."""

import telegram


class TextMessage:
    """Telegram text message."""

    id: int
    """The message ID."""
    topic_id = None
    """The topic ID if any."""
    chat: "TelegramChat"
    """The chat in which the message was sent."""
    user: "TelegramUser"
    """The user who sent the message."""
    reply = None
    """The message to which this message is a reply if any."""
    text: str
    """The message text."""

    @property
    def session(self) -> str:
        """The session ID of the message."""
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

    def to_chat_message(self):
        """Convert the message to a chat model message."""
        pass

    @classmethod
    def from_telegram_message(cls, message: telegram.Message) -> None:
        """Initialize a text message from a Telegram message.

        Args:
            message (Message): The update's message.
        """

        # create message
        message_instance = cls()
        message_instance.id = message.message_id
        message_instance.chat = TelegramChat.from_telegram_chat(message.chat)
        message_instance.user = TelegramUser.from_telegram_user(
            message.from_user or message.sender_chat or message.chat
        )

        # fill-in the topic if any
        if message.is_topic_message and message.message_thread_id:
            message_instance.topic_id = message.message_thread_id
        # fill-in reply message if any
        if reply := message.reply_to_message:
            message_instance.reply = TextMessage(reply)

        message_instance.text = message.text or message.caption or ""
        return message_instance


class TelegramChat:
    """Telegram chat."""

    id: int
    """The chat ID."""
    title: str = ""
    """The chat title if any."""
    _username = None

    @property
    def username(self) -> str:
        """The chat's username. The chat title if no username."""

        return self._username or self.title

    @classmethod
    def from_telegram_chat(cls, chat: telegram.Chat) -> None:
        """Initialize a chat from a Telegram chat.

        Args:
            chat (Chat): The update's chat.
        """

        chat_instance = cls()
        chat_instance.id = chat.id
        chat_instance.title = chat.title or chat_instance.title
        chat_instance._username = chat.username
        return chat_instance


class TelegramUser:
    """Telegram user."""

    id: int
    """The user ID."""
    first_name: str
    """The user first name if any."""
    last_name: str | None = None
    """The user last name if any."""
    _username = None

    @property
    def username(self) -> str:
        """The user's username. The user's fullname if no username."""

        return self._username or self.fullname

    @property
    def fullname(self) -> str:
        """The user's fullname."""

        first_last = f"{self.first_name} {self.last_name or ''}"
        return first_last.strip()

    @classmethod
    def from_telegram_user(cls, user: telegram.User | telegram.Chat) -> None:
        """Initialize a user from a Telegram user.

        Args:
            user (User): The update's user.
        """

        user_instance = cls()
        user_instance.id = user.id
        user_instance._username = user.username
        user_instance.last_name = user.last_name

        # first name is title for chats
        if isinstance(user, telegram.Chat):
            user_instance.first_name = TelegramChat(user).title
        else:
            user_instance.first_name = user.first_name

        return user_instance
