"""Utility functions for the database module."""

from sqlalchemy.orm import Session

from database import core as db
from database.models import Chat, Message, User


def get_user(user_id: int) -> User | None:
    """Get the user with the given ID if it exists."""

    with Session(db.engine) as session:
        return session.get(User, user_id)


def add_user(user: User) -> None:
    """Add a new user or update an existing one."""

    with Session(db.engine) as session:
        session.merge(user)
        session.commit()


def get_chat(chat_id: int) -> Chat | None:
    """Get the chat with the given ID if it exists."""

    with Session(db.engine) as session:
        return session.get(Chat, chat_id)


def add_message(message: Message) -> None:
    """Add or update a message. Creates new chat if none exists."""

    # create chat if it doesn't exist
    if not message.chat:
        message.chat = Chat(id=message.chat_id)
    # assign user if not assigned
    if not message.user:
        message.user = User(id=message.user_id)

    # store message
    with Session(db.engine) as session:
        session.merge(message)
        session.commit()
