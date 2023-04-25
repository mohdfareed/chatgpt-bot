"""Utility functions for the database module."""

from database.models import Chat, Message, User


def get_user(user_id: int) -> User:
    """Get the user with the given ID if it exists."""
    from database.core import session_maker

    with session_maker() as session:
        return session.query(User).filter_by(id=user_id).first()


def add_user(user: User) -> None:
    """Add a new user or update an existing one."""
    from database.core import session_maker

    with session_maker() as session:
        session.add(user) if not get_user(user.id) else session.merge(user)
        session.commit()


def get_chat(chat_id: int) -> Chat:
    """Get the chat with the given ID if it exists."""
    from database.core import session_maker

    with session_maker() as session:
        return session.query(Chat).filter_by(id=chat_id).first()


def add_chat(chat: Chat) -> None:
    """Add a new chat or update an existing one."""
    from database.core import session_maker

    with session_maker() as session:
        session.add(chat) if not get_chat(chat.id) else session.merge(chat)
        session.commit()


def get_message(message_id: int, chat_id: int) -> Message:
    """Get the message with the given ID if it exists."""
    from database.core import session_maker

    with session_maker() as session:
        return session.query(Message).filter_by(
            id=message_id, chat_id=chat_id).first()


def add_message(message: Message) -> None:
    """Add or update a message. Creates new chat if none exists."""
    from database.core import session_maker

    # create chat if it doesn't exist
    add_chat(Chat(id=message.chat_id)) if not message.chat else None
    # store message
    with session_maker() as session:
        session.add(message) if not get_message(
            message.id, message.chat_id
        ) else session.merge(message)
        session.commit()
