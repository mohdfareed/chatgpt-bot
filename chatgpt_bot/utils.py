"""Utility for interfacing with the database. Defines parsers for telegram
objects into database objects."""

from telegram import Chat, Message, User

from database import models


def parse_message(message: Message) -> models.Message:
    """Parse a telegram update message into a database message."""
    db_message = models.Message()

    # create message
    db_message.id = message.message_id
    db_message.chat_id = message.chat_id
    # fill-in the topic if any
    if message.is_topic_message and message.message_thread_id:
        db_message.topic_id = message.message_thread_id
    # fill-in the user if any
    if user := message.from_user:
        db_message.user_id = user.id
    # fill-in reply message if any
    if reply := message.reply_to_message:
        if message.is_topic_message:
            # don't include the reply if it's the topic creation message
            if reply.message_id != message.message_thread_id:
                db_message.reply_id = reply.message_id
        else:
            db_message.reply_id = reply.message_id
    # fill-in the text if any
    if text := message.text:
        db_message.text = text

    return db_message


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
    db_user.username = user.username

    return db_user
