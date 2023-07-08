"""The database models defining the database schema."""

import typing

import sqlalchemy as sql
import sqlalchemy.ext.asyncio as async_sql
import sqlalchemy.orm as orm
import sqlalchemy_utils
from sqlalchemy_utils.types.encrypted import encrypted_type
from typing_extensions import override

import database

_encrypted = sqlalchemy_utils.StringEncryptedType(
    sql.Unicode, database.encryption_key, encrypted_type.FernetEngine
)


class Chat(database.core.DatabaseModel):
    """A chat session with a chat model."""

    __tablename__ = "chats"

    chat_id: orm.Mapped[str] = orm.mapped_column(unique=True)
    """The chat's unique ID."""
    messages: orm.Mapped[list["Message"]] = orm.relationship()
    """The chat's messages."""
    data: orm.Mapped[str | None] = orm.mapped_column(_encrypted)
    """The chat's data."""

    def __init__(
        self,
        id: int | None = None,
        chat_id: str | None = None,
        data: str | None = None,
        engine: async_sql.AsyncEngine | None = None,
        **kw: typing.Any
    ):
        super().__init__(
            id=id,
            chat_id=chat_id,
            data=data,
            engine=engine,
            **kw,
        )

    @property
    @override
    def _loading_statement(self):
        return (
            sql.select(type(self))
            .where(
                (type(self).id == self.id)
                | (type(self).chat_id == self.chat_id)
            )
            .options(orm.selectinload(type(self).messages))
        )


class Message(database.core.DatabaseModel):
    """A message in a chat."""

    __tablename__ = "messages"

    message_id: orm.Mapped[str] = orm.mapped_column()
    """The message's ID. Unique within a chat."""
    chat_id: orm.Mapped[str] = orm.mapped_column(sql.ForeignKey(Chat.chat_id))
    """The ID of the chat to which the message belongs."""
    data: orm.Mapped[str] = orm.mapped_column(_encrypted, default="{}")
    """The message's data."""

    def __init__(
        self,
        id: int | None = None,
        message_id: str | None = None,
        chat_id: str | None = None,
        data: str | None = None,
        engine: async_sql.AsyncEngine | None = None,
        **kw: typing.Any
    ):
        super().__init__(
            id=id,
            message_id=message_id,
            chat_id=chat_id,
            data=data,
            engine=engine,
            **kw,
        )

    @override
    async def save(self):
        # create the chat if it doesn't exist
        await (await Chat(chat_id=self.chat_id).load()).save()
        # save the message
        await super().save()

    # message id and chat id are a unique combination
    __table_args__ = (sql.UniqueConstraint("message_id", "chat_id"),)
