"""Utility functions for the database module. It is responsible for managing
objects in the database."""

from typing import Optional

from sqlalchemy.orm import Session, selectinload

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
    """Add a new chat or update an existing one.

    Args:
        chat (Chat): The chat to add or update.
    """

    with Session(db.engine) as session:
        session.merge(chat)
        session.commit()


def get_topic(topic_id: int, chat_id: int) -> Topic:
    """Get the forum topic with the given chat ID and topic ID if it exists.

    Args:
        chat_id (int): The ID of the chat containing the topic.
        topic_id (int): The ID of the topic.

    Returns:
        Topic: The topic with the given chat ID and topic ID, or a new topic if
        it does not exist.
    """

    # get new topic if topic doesn't exist
    with Session(db.engine) as session:
        return (session.get(Topic, (chat_id, topic_id)) or
                Topic(id=topic_id, chat_id=chat_id))


def add_topic(topic: Topic) -> None:
    """Add or update a forum topic.

    Args:
        topic (Topic): The topic to add or update.
    """

    # create chat if none exists
    if not topic.chat:
        topic.chat = Chat(id=topic.chat_id)

    with Session(db.engine) as session:
        session.merge(topic)
        session.commit()


def get_user(user_id: int) -> User:
    """Get the user with the given ID if it exists.

    Args:
        user_id (int): The ID of the user.

    Returns:
        User: The user with the given ID, or a new user if it does not exist.
    """

    with Session(db.engine) as session:
        return session.get(User, user_id) or User(id=user_id)


def add_user(user: User) -> None:
    """Add or update a user.

    Args:
        user (User): The user to add or update.
    """

    with Session(db.engine) as session:
        session.merge(user)
        session.commit()


def get_message(message_id: int, chat_id: int) -> Message:
    """Get the message with the given ID and chat ID if it exists.

    Args:
        message_id (int): The ID of the message.
        chat_id (int): The ID of the chat containing the message.

    Returns:
        Message: The message with the given ID and chat ID, or a new message if
        it does not exist.
    """

    with Session(db.engine) as session:
        return (session.get(Message, (message_id, chat_id)) or
                Message(id=message_id, chat_id=chat_id))


def add_message(message: Message) -> None:
    """Add or update a message. Creates new chat if none exists. It created new
    user, chat, topic, and reply message objects if any do not exist.

    Args:
        message (Message): The message to add or update.
    """

    # create chat if none exists
    message.chat = get_chat(message.chat_id)
    # create topic if none exists
    if message.topic_id:
        message.topic = get_topic(message.topic_id, message.chat_id)
    # create user if none exists
    if message.user_id:
        message.user = get_user(message.user_id)
    # create reply message in same topic if none exists
    if message.reply_id:
        message.reply_to = get_message(message.reply_id, message.chat_id)
        message.reply_to.topic_id = message.topic_id

    # TODO: fix reply if topic message (telegram bug)
    # since a topic is a message thread, if a message is not a reply, it is
    # considered a reply to the topic creation message if part of one
    if message.reply_id == message.topic_id:
        message.reply_id, message.reply_to = None, None

    with Session(db.engine) as session:
        session.merge(message)
        session.commit()


def get_messages(chat_id: int, topic_id: int | None = None) -> list[Message]:
    """Get all messages in a chat or topic. The messages are sorted by their
    message ID.

    Args:
        chat_id (int): The ID of the chat containing the messages.
        topic_id (int, optional): The ID of the topic containing the messages,
        if any.
    """

    with Session(db.engine) as session:
        # load all messages in chat
        query = session.query(Message).filter(
            Message.chat_id == chat_id).options(selectinload('*'))
        if topic_id:  # filter by topic if given
            query = query.filter(Message.topic_id == topic_id)
        else:  # get general chat messages if no topic given
            query = query.filter(Message.topic_id == None)
        query = query.order_by(Message.id)
        return query.all()


def get_system_message(chat_id: int, topic_id: int | None = None) -> Message:
    """Get the system message for a chat or topic.

    Args:
        chat_id (int): The ID of the chat containing the messages.
        topic_id (int, optional): The ID of the topic containing the messages,
        if any.
    """

    return get_message(-(topic_id or 0), chat_id)


def delete_messages(chat_id: int, topic_id: Optional[int] = None) -> None:
    """Delete all messages in a chat or topic. Does not delete system messages.

    Args:
        chat_id (int): The ID of the chat containing the messages.
        topic_id (int, optional): The ID of the topic containing the messages,
        if any.
    """

    with Session(db.engine) as session:
        query = session.query(Message).filter(Message.chat_id == chat_id)
        query = query.filter(Message.id > 0)
        if topic_id:
            query = query.filter(Message.topic_id == topic_id)
        else:
            query = query.filter(Message.topic_id == None)
        query.delete()
        session.commit()
