"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import abc
import inspect

import telegram
import telegram.constants
import telegram.ext as telegram_extensions
from typing_extensions import override

from bot import core, metrics, utils

_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE
_mention = telegram.constants.MessageEntityType.MENTION


class MessageHandler(abc.ABC):
    """Base class for telegram update handlers of messages."""

    filters = ~telegram_extensions.filters.Command(False)
    """The message update filters."""
    block: bool | None = None
    """Whether the message handler should block other handlers."""
    group: int = 10
    """The handler's group. Handlers in the same group are mutually exclusive.
    Lower group numbers have higher priority."""

    @property
    def handler(self) -> telegram_extensions.MessageHandler:
        """The message handler."""
        handler = telegram_extensions.MessageHandler(
            callback=self.callback,
            filters=self.filters,
        )
        # set blocking if specified, use default otherwise
        if self.block is not None:
            handler.block = self.block
        return handler

    @staticmethod
    @abc.abstractstaticmethod
    async def callback(update: telegram.Update, context: _default_context):
        """The callback function for the command."""
        pass

    @classmethod
    def all_handlers(cls):
        """Returns all the handlers."""
        import bot.settings

        if not inspect.isabstract(cls):
            yield cls()  # type: ignore
        for sub_handler in cls.__subclasses__():
            yield from sub_handler.all_handlers()


class PrivateMessageHandler(MessageHandler):
    """Handle a private message."""

    filters = (
        MessageHandler.filters
        & telegram_extensions.filters.ChatType.PRIVATE
        & telegram_extensions.filters.UpdateType.MESSAGES
    )

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        # reply to new messages
        if update.message or update.channel_post:
            await utils.reply_to_user(message, reply=False)
        else:  # if a message was edited
            await utils.add_message(message) if message.text else None


class GroupMessageHandler(MessageHandler):
    """Handle a group message."""

    filters = (
        MessageHandler.filters
        & telegram_extensions.filters.ChatType.GROUPS
        & telegram_extensions.filters.UpdateType.MESSAGES
    )

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        try:  # check if text message was received
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        # add edited messages
        if not (update.message or update.channel_post):
            await utils.add_message(message)
            return  # don't reply to edited messages

        # check bot reply mode
        chat = await metrics.TelegramMetrics(entity_id=message.chat_id).load()
        if not chat.reply_to_mentions:
            # reply to all messages
            await utils.reply_to_user(message)

        else:  # reply only to mentions of the bot
            if _is_bot_mention(message, context.bot.username):
                await utils.reply_to_user(message, reply=True)
            else:  # store other messages as context
                await utils.add_message(message)


class PinServiceHandler(MessageHandler):
    """Handle a pinning update of messages."""

    filters = (
        MessageHandler.filters & telegram_extensions.filters.UpdateType.MESSAGE
    )
    group = 5

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        if not (update_message := update.effective_message):
            return
        if not (pinned_message := update_message.pinned_message):
            return
        message = core.TextMessage(pinned_message)
        await utils.pin_message(message)
        raise telegram_extensions.ApplicationHandlerStop


def _is_bot_mention(message: core.TelegramMessage, bot_username: str):
    entities = message.telegram_message.parse_caption_entities([_mention])
    entities.update(message.telegram_message.parse_entities([_mention]))
    return f"@{bot_username}" in entities.values()
