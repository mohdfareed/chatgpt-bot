"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import abc
import inspect

import telegram
import telegram.constants
import telegram.ext as telegram_extensions

import chatgpt.memory
import chatgpt.model
from bot import chat_handler, models

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

    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.message or update.channel_post):
            return  # TODO: update edited messages (user effective message)
        message = models.TextMessage(update_message)

        history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
        await history.add_message(message.to_chat_message())


class PrivateMessageHandler(MessageHandler):
    """Handle a private message."""

    filters = MessageHandler.filters & (
        telegram_extensions.filters.ChatType.PRIVATE
        | telegram_extensions.filters.Entity(
            telegram.constants.MessageEntityType.MENTION
        )
    )

    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        if not (update_message := update.message or update.channel_post):
            return
        message = models.TextMessage(update_message)

        await _reply_to_user(  # reply only to mentions
            message, reply=(f"@{context.bot.name}" in message.text)
        )


def all_handlers(handler=MessageHandler):
    """All available update handlers.
    Recursively yields all concrete subclasses of the base class."""
    if not inspect.isabstract(handler):
        yield handler()  # type: ignore
    for subcommand in handler.__subclasses__():
        yield from all_handlers(subcommand)


async def _reply_to_user(message: models.TextMessage, reply=False):
    # create handler
    message_handler = chat_handler.ModelMessageHandler(message, reply=reply)
    # initialize model's memory
    memory = await chatgpt.memory.ChatMemory.initialize(
        message.chat_id, 3500, 2500
    )
    # setup the model
    model = chatgpt.model.ChatModel(
        memory=memory,
        handlers=[message_handler],
    )
    # generate a reply
    return await model.run(message.to_chat_message())
