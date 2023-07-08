"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import abc
import inspect

import telegram
import telegram.constants
import telegram.ext as telegram_extensions
from typing_extensions import override

import chatgpt.model
from bot import models, utils

_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE


class MessageHandler(abc.ABC):
    """Base class for telegram update handlers of messages."""

    filters = ~telegram_extensions.filters.Command(False)
    """The message update filters."""
    block: bool | None = None
    """Whether the message handler should block other handlers."""
    group: int = 0
    """The handler's group. Handlers in the same group are mutually exclusive.
    Lower group numbers have higher priority."""

    @property
    def handler(self) -> telegram_extensions.MessageHandler:
        """The message handler."""
        handler = telegram_extensions.MessageHandler(
            callback=type(self).callback,
            filters=type(self).filters,
        )
        # set blocking if specified, use default otherwise
        if self.block is not None:
            handler.block = self.block
        return handler

    @staticmethod
    @abc.abstractmethod
    async def callback(update: telegram.Update, context: _default_context):
        """The callback function for the command."""
        pass


class ConversationHandler(MessageHandler):
    """Stores conversation messages as context to the chat's model."""

    filters = MessageHandler.filters & (
        ~telegram_extensions.filters.ChatType.PRIVATE
        & ~telegram_extensions.filters.Entity(
            telegram.constants.MessageEntityType.MENTION
        )
    )

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return
        message = models.TextMessage(update_message)
        await utils.add_message(message)


class PrivateMessageHandler(MessageHandler):
    """Handle a private message."""

    filters = MessageHandler.filters & (
        telegram_extensions.filters.ChatType.PRIVATE
        | telegram_extensions.filters.Entity(
            telegram.constants.MessageEntityType.MENTION
        )
    )

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        if not (update_message := update.message or update.channel_post):
            return
        message = models.TextMessage(update_message)

        await utils.reply_to_user(
            message, reply=(f"@{context.bot.name}" in message.text)
        )  # reply only to mentions


def all_handlers(handler=MessageHandler):
    """All available update handlers.
    Recursively yields all concrete subclasses of the base class."""
    if not inspect.isabstract(handler):
        yield handler()  # type: ignore
    for sub_handler in handler.__subclasses__():
        yield from all_handlers(sub_handler)
