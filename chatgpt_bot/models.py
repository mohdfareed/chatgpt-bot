"""Models of Telegram entities."""

import telegram as _telegram


class TextMessage:
    """Telegram text message."""

    id: int
    """The message ID."""
    chat_id: int
    """The chat ID."""
    topic_id: int | None
    """The topic ID if any."""
    reply_id: int | None
    """The reply message ID if any."""
    user: "TelegramUser"
    """The user who sent the message."""
    text: str
    """The message text."""

    @property
    def session_id(self) -> str:
        """The session ID of the message."""
        return f"{self.chat_id}_{self.topic_id or '-1'}"

    @property
    def metadata(self) -> dict[str, str]:
        """The message metadata."""
        metadata = dict(
            id=str(self.id),
            username=self.user.username,
            reply_id=str(self.reply_id) if self.reply_id else None,
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
        self.chat_id = message.chat_id
        self.text = message.text or message.caption or ""
        self.user = TelegramUser(message.from_user or message.sender_chat)

        # fill-in the topic if any
        self.topic_id = None
        if message.is_topic_message and message.message_thread_id:
            self.topic_id = message.message_thread_id

        # fill-in reply message if any
        self.reply_id = None
        if reply := message.reply_to_message:
            self.reply_id = reply.message_id


class TelegramUser:
    """Telegram user."""

    id: int = -1
    """The user ID."""
    first_name: str | None = None
    """The user first name if any."""
    last_name: str | None = None
    """The user last name if any."""
    _username = None

    @property
    def username(self) -> str:
        """The user's username. An empty string if no username, first, nor
        last name."""

        first_last = f"{self.first_name or ''} {self.last_name or ''}"
        return self._username or first_last.strip()

    @property
    def fullname(self) -> str:
        """The user's fullname. An empty string if no username, first, nor
        last name."""

        first_last = f"{self.first_name or ''} {self.last_name or ''}"
        return first_last.strip() or self._username or ""

    def __init__(self, user: _telegram.User | _telegram.Chat | None) -> None:
        """Initialize a user from a Telegram user.

        Args:
            user (User): The update's user.
        """

        # create unknown user
        if not user:
            return

        # create user
        self.id = user.id
        self.first_name = user.first_name
        self.last_name = user.last_name
        self._username = user.username

        # set chat title as first name if any
        if isinstance(user, _telegram.Chat) and user.title:
            self.first_name = user.title
