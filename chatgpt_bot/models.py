"""Models of Telegram entities."""

import telegram as _telegram


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
        return f"{self.chat.id}_{self.topic_id or '-1'}"

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

    def __init__(self, message: _telegram.Message) -> None:
        """Initialize a text message from a Telegram message.

        Args:
            message (Message): The update's message.
        """

        # create message
        self.id = message.message_id
        self.chat = TelegramChat(message.chat)
        self.user = TelegramUser(
            message.from_user or message.sender_chat or message.chat
        )

        # fill-in the topic if any
        if message.is_topic_message and message.message_thread_id:
            self.topic_id = message.message_thread_id
        # fill-in reply message if any
        if reply := message.reply_to_message:
            self.reply = TextMessage(reply)

        self.text = message.text or message.caption or ""


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

    def __init__(self, chat: _telegram.Chat) -> None:
        """Initialize a chat from a Telegram chat.

        Args:
            chat (Chat): The update's chat.
        """

        # create chat
        self.id = chat.id
        self.title = chat.title or self.title
        self._username = chat.username


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

    def __init__(self, user: _telegram.User | _telegram.Chat) -> None:
        """Initialize a user from a Telegram user.

        Args:
            user (User): The update's user.
        """

        self.id = user.id
        self._username = user.username
        self.last_name = user.last_name

        # first name is title for chats
        if isinstance(user, _telegram.Chat):
            self.first_name = TelegramChat(user).title
        else:
            self.first_name = user.first_name
