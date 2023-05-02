"""Utility functions for the database module. It is responsible for managing
objects in the database."""

from sqlalchemy.orm import Session

from database import core as db
from database.models import Chat, Message, Topic, User


def get_chat(chat_id: int) -> Chat:
    """Get the chat with the given ID if it exists.

    Args:
        chat_id (int): The ID of the chat.

    Returns:
        Chat: The chat with the given ID, or a new chat if it does not exist.
    """

    with Session(db.engine) as session:
        return session.get(Chat, chat_id) or Chat(id=chat_id)


def add_chat(chat: Chat) -> None:
    """Add a new chat or update an existing one."""

    with Session(db.engine) as session:
        session.merge(chat)
        session.commit()


def get_topic(chat_id: int, topic_id: int) -> Topic:
    """Get the forum topic with the given chat ID and topic ID if it exists.
    """

    # get new topic if topic doesn't exist
    with Session(db.engine) as session:
        return (session.get(Topic, (chat_id, topic_id)) or
                Topic(chat_id=chat_id, topic_id=topic_id))


def add_topic(topic: Topic) -> None:
    """Add or update a forum topic."""

    # create chat if none exists
    if not topic.chat:
        topic.chat = Chat(id=topic.chat_id)

    with Session(db.engine) as session:
        session.merge(topic)
        session.commit()


def get_user(user_id: int) -> User:
    """Get the user with the given ID if it exists."""

    with Session(db.engine) as session:
        return session.get(User, user_id) or User(id=user_id)


def add_user(user: User) -> None:
    """Add or update a user."""

    with Session(db.engine) as session:
        session.merge(user)
        session.commit()


def get_message(message_id: int, chat_id: int) -> Message:
    """Get the message with the given ID and chat ID if it exists."""

    with Session(db.engine) as session:
        return (session.get(Message, (message_id, chat_id)) or
                Message(id=message_id, chat_id=chat_id))


def add_message(message: Message) -> None:
    """Add or update a message. Creates new chat if none exists."""

    # create chat if none exists
    if not message.chat:
        message.chat = Chat(id=message.chat_id)
    # fix reply if to a topic (telegram bug)
    if message.reply_id == message.topic_id:
        message.reply_id = None

    # store message
    with Session(db.engine) as session:
        session.merge(message)
        session.commit()
