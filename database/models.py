"""The models defining the database schema."""

from typing import Optional

from chatgpt.types import MessageRole
from sqlalchemy import BigInteger, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """The base class for all database models."""
    pass


class Chat(Base):
    """A telegram private chat (user), group chat, or channel."""
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The chat's ID."""
    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    """The chat's cumulative token usage."""

    def __repr__(self):
        return f"<Chat(id={self.id})>"


class Topic(Base):
    """A chat forum topic."""
    __tablename__ = "topic"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The topic's ID. 0 for general chat."""
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    """The ID of the chat the topic was created in."""

    chat: Mapped[Chat] = relationship()
    """The chat the topic was created in."""
    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    """The topic's cumulative token usage."""

    def __repr__(self):
        return f"<Topic(topic_id={self.id}, chat_id={self.chat_id})>"


class User(Base):
    """A telegram user."""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The user's ID."""
    username: Mapped[Optional[str]] = mapped_column()
    """The user's Telegram username."""
    usage: Mapped[int] = mapped_column(BigInteger, default=0)
    """The user's cumulative token usage."""

    def __repr__(self):
        return f"<Topic(id={self.id}, username={self.username})>"


class Message(Base):
    """A message sent in a chat. Chat prompts have negative IDs."""
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The ID of the message."""

    # chat
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    """The ID of the chat the message was sent in."""
    chat: Mapped[Chat] = relationship()
    """The chat the message was sent in."""

    # topic
    topic_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the chat the message was sent in."""
    topic: Mapped[Optional[Topic]] = relationship(
        primaryjoin=(topic_id == Topic.id and  # type: ignore
                     chat_id == Topic.chat_id) # type: ignore
    )
    """The topic the message was sent in, if any."""

    # reply
    reply_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the message this message is a reply to, if any."""
    reply_to: Mapped[Optional["Message"]] = relationship(
        primaryjoin=(reply_id == id and  # type: ignore
                     chat_id == chat_id), # type: ignore
        remote_side=[id]
    )
    """The message this message is a reply to, if any."""

    # user
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey(User.id))
    """The ID of the user who sent the message, if any."""
    user: Mapped[Optional[User]] = relationship()
    """The user who sent the message, if any."""

    # openai data
    role: Mapped[MessageRole] = mapped_column(default=MessageRole.USER)
    """The role under which the message was sent."""
    finish_reason: Mapped[Optional[str]] = mapped_column()
    """The reason the message content terminated, if any."""
    prompt_tokens: Mapped[Optional[int]] = mapped_column()
    """The number of tokens in the prompt."""
    reply_tokens: Mapped[Optional[int]] = mapped_column()
    """The number of tokens in the reply."""
    name: Mapped[Optional[str]] = mapped_column()
    """The name of the OpenAI message, if any."""

    # telegram data
    text: Mapped[Optional[str]] = mapped_column()
    """The message's text."""

    __table_args__ = (
        ForeignKeyConstraint(
            ["topic_id", "chat_id"], ["topic.id", "topic.chat_id"]
        ),
        ForeignKeyConstraint(
            ["reply_id", "chat_id"], ["message.id", "message.chat_id"]
        )
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role})>"
