"""The models defining the database schema."""

from typing import List, Optional

from chatgpt.message import Prompt
from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """The base class for all models."""
    pass


class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    messages: Mapped[List["Message"]] = relationship(back_populates="chat")
    """The chat's messages."""
    users: Mapped[List["User"]] = relationship(back_populates="chats",
                                               secondary="messages",
                                               overlaps="messages")
    """The chat's users."""

    def __repr__(self):
        return f"<Chat(id={self.id})>"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column()
    """The user's Telegram username."""
    usage: Mapped[int] = mapped_column(default=0)
    """The user's cumulative token usage."""
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    """The user's messages."""
    chats: Mapped[List[Chat]] = relationship(back_populates="users",
                                             secondary="messages",
                                             overlaps="messages")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)

    # identifiers
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
    """The ID of the user who sent the message, if known."""
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    """The ID of the chat the message was sent in."""
    topic_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the topic under which the message was sent, if any."""

    # relationships
    chat: Mapped[Chat] = relationship(back_populates="messages",
                                      overlaps="chats,users")
    """The chat the message was sent in."""
    user: Mapped[User] = relationship(back_populates="messages",
                                      overlaps="chats,users")
    """The user who sent the message."""

    # openai data
    role: Mapped[str] = mapped_column(default=Prompt.ROLES[0])
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
    is_edited: Mapped[bool] = mapped_column(default=False)
    """Whether the message has been edited."""
    is_deleted: Mapped[bool] = mapped_column(default=False)
    """Whether the message has been deleted."""

    def __repr__(self) -> str:
        s = f"{self.text[:15]}{'...' if len(self.text) > 15 else ''}"
        return f"<Message(user={self.user.id}, content={s})>"
