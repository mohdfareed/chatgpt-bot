"""The models defining the database schema."""

from typing import List, Optional

from chatgpt.message import Prompt
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
    messages: Mapped[List["Message"]] = relationship(back_populates="chat")
    """The chat's messages. This is the general topic for forums."""
    topics: Mapped[List["Topic"]] = relationship(back_populates="chat")
    """The chat's topics."""
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

    chat: Mapped[Chat] = relationship(back_populates="topics")
    """The chat the topic was created in."""
    messages: Mapped[List["Message"]] = relationship(
        primaryjoin=("Message.topic_id == Topic.id and "
                     "Message.chat_id == Topic.chat_id"),
        overlaps="messages",
        back_populates="topic")
    """The topic's messages."""

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

    # relationships
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    """The user's messages."""

    def __repr__(self):
        return f"<Topic(id={self.id}, username={self.username})>"


class Message(Base):
    """A message sent in a chat."""
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """The ID of the message."""

    # chat
    chat_id: Mapped[int] = mapped_column(ForeignKey(Chat.id), primary_key=True)
    """The ID of the chat the message was sent in."""
    chat: Mapped[Chat] = relationship(back_populates="messages")
    """The chat the message was sent in."""

    # topic
    topic_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the chat the message was sent in."""
    topic: Mapped[Topic] = relationship(
        primaryjoin=topic_id == Topic.id and chat_id == Topic.chat_id,
        back_populates="messages")
    """The topic the message was sent in, if any."""

    # reply
    reply_id: Mapped[Optional[int]] = mapped_column()
    """The ID of the message this message is a reply to, if any."""
    reply_to: Mapped[Optional["Message"]] = relationship(
        primaryjoin=reply_id == id and chat_id == chat_id,
        remote_side=[id], back_populates="replies")
    """The message this message is a reply to, if any."""
    replies: Mapped[List["Message"]] = relationship(
        primaryjoin=id == reply_id and chat_id == chat_id,
        back_populates="reply_to")
    """The messages that are replies to this message."""

    # user
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey(User.id))
    """The ID of the user who sent the message, if any."""
    user: Mapped[Optional[User]] = relationship(back_populates="messages")
    """The user who sent the message, if any."""

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
