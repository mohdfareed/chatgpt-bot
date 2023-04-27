"""The models defining the database schema."""

from typing import List, Optional

from chatgpt.message import Prompt
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """The base class for all database models."""
    pass


class Chat(Base):
    __tablename__ = "chats"

    def __init__(self, id: int, **kw):
        super().__init__(id=id, **kw)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The chat's ID."""
    messages: Mapped[List["Message"]] = relationship(back_populates="chat")
    """The chat's messages."""

    def __repr__(self):
        return f"<Chat(id={self.id})>"


class User(Base):
    __tablename__ = "users"

    def __init__(self, id: int, **kw):
        super().__init__(id=id, **kw)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The user's Telegram ID."""
    usage: Mapped[int] = mapped_column(default=0)
    """The user's cumulative token usage."""
    username: Mapped[Optional[str]] = mapped_column()
    """The user's Telegram username."""
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    """The user's messages."""

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Message(Base):
    __tablename__ = "messages"

    def __init__(self, id: int, chat_id: int, user: User, **kw):
        super().__init__(id=id, chat_id=chat_id, user=user, **kw)

    # identifiers
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The ID of the message."""
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    """The ID of the chat the message was sent in."""
    topic_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the topic under which the message was sent, if any."""
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    """The ID of the user who sent the message."""

    # relationships
    user: Mapped[User] = relationship()
    """The user who sent the message."""
    chat: Mapped[Chat] = relationship(back_populates="messages")
    """The chat the message was sent in."""

    # openai data
    role: Mapped[str] = mapped_column(default=Prompt.Role.USER)
    """The role under which the message was sent."""
    finish_reason: Mapped[Optional[str]] = mapped_column()
    """The reason the message content terminated, if any."""
    prompt_tokens: Mapped[Optional[int]] = mapped_column()
    """The number of tokens in the prompt."""
    reply_tokens: Mapped[Optional[int]] = mapped_column()
    """The number of tokens in the reply."""

    # telegram data
    text: Mapped[str] = mapped_column()
    """The message's text."""

    def __repr__(self) -> str:
        s = f"{self.text[:15]}{'...' if len(self.text) > 15 else ''}"
        return f"<Message(user={self.user.id}, content={s})>"
