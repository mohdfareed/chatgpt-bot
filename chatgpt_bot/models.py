"""Models of Telegram entities."""

from telegram import Chat, Message, User

from database import models


class TextMessage:
    """Telegram text message."""

    def __init__(self, message: Message) -> None:
        """Initialize a text message from an Telegram message.

        Args:
            message (Message): The update's message.
        """

        # create message
        self.id = message.message_id
        self.chat_id = message.chat_id
        self.text = message.text or message.caption or ""

        # fill-in the topic if any
        self.topic_id = None
        if message.is_topic_message and message.message_thread_id:
            self.topic_id = message.message_thread_id

        # # fill-in the user if any
        # if user := message.from_user:
        #     db_message.user_id = user.id

        # # fill-in reply message if any
        # if reply := message.reply_to_message:
        #     db_message.reply_id = reply.message_id


def parse_chat(chat: Chat) -> models.Chat:
    """Parse a telegram update chat into a database chat."""
    db_chat = models.Chat()

    # create chat
    db_chat.id = chat.id

    return db_chat


def parse_topic(message: Message) -> models.Topic:
    """Parse a telegram update message into a database topic."""
    db_topic = models.Topic()

    # create a topic if any
    if topic_id := message.message_thread_id:
        db_topic.id = topic_id
        db_topic.chat_id = message.chat_id

    return db_topic


def parse_user(user: User) -> models.User:
    """Parse a telegram update user into a database user."""
    db_user = models.User()

    # create user
    db_user.id = user.id
    if user.username:
        db_user.username = user.username
    else:  # use first and last name if no username
        db_user.username = f'{user.first_name}{str(user.last_name or "")}'

    return db_user
