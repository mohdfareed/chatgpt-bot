"""The models defining the database schema."""

from typing import List, Optional

from chatgpt.message import Prompt
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """The base class for all models."""
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column()
    """The user's Telegram username."""
    usage: Mapped[int] = mapped_column(default=0)
    """The user's cumulative token usage."""

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(primary_key=True)

    messages: Mapped[List["Message"]] = relationship(back_populates="chat")
    """The chat's messages."""

    def __repr__(self):
        return f"<Chat(id={self.id})>"


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)

    # identifiers
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    topic_id: Mapped[Optional[int]]  # the topic within a group
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))

    # relationships
    chat: Mapped[Chat] = relationship(back_populates="messages")
    user: Mapped[User] = relationship(User)

    # openai data
    role: Mapped[str] = mapped_column(default=Prompt.ROLES[0])
    finish_reason: Mapped[Optional[str]] = mapped_column()
    prompt_tokens: Mapped[Optional[int]] = mapped_column()
    reply_tokens: Mapped[Optional[int]] = mapped_column()

    # telegram data
    text: Mapped[str] = mapped_column()
    """The message's text."""
    is_edited: Mapped[bool] = mapped_column(default=False)
    """Whether the message has been edited."""
    is_deleted: Mapped[bool] = mapped_column(default=False)
    """Whether the message has been deleted."""

    def __repr__(self) -> str:
        s = f"{self.text[:15]}{'...' if len(self.text) > 15 else ''}"
        return f"<Message(user={self.user.id}, content={s})>"
