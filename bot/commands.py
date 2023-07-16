"""Command handlers for telegram command updates. It is responsible for parsing
updates and executing core module functionality."""

import abc
import inspect
import textwrap

import telegram
import telegram.ext as telegram_extensions
from typing_extensions import override

import database.core
from bot import core, formatter, handlers, telegram_utils, utils

_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE


class Command(handlers.MessageHandler, abc.ABC):
    """Base class for bot commands. All commands inherit from this class."""

    names: tuple[str, ...]
    """The names that trigger the command. The first is the primary name."""
    description: str
    """The command's description."""
    filters = telegram_extensions.filters.Command(False)
    """The command update filters. Defaults to all commands."""

    @property
    def handler(self) -> telegram_extensions.CommandHandler:
        """The command handler."""
        handler = telegram_extensions.CommandHandler(
            command=self.names,
            callback=self.callback,
            filters=self.filters,
        )
        # set blocking if specified, use default otherwise
        if self.block is not None:
            handler.block = self.block
        return handler

    @property
    def bot_command(self) -> telegram.BotCommand:
        return telegram.BotCommand(self.names[0], self.description)

    @classmethod
    def all_commands(cls):
        """Returns all the commands."""
        import bot.settings

        if not inspect.isabstract(cls):
            yield cls()  # type: ignore
        for subcommand in cls.__subclasses__():
            yield from subcommand.all_commands()


class Help(Command):
    names = ("help",)
    description = "Show the help message"

    help_message = textwrap.dedent(
        """
        WIP
        """
    ).strip()

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        dummy_message = formatter.format_message(Help.help_message)
        dummy_message = dummy_message.format(bot=context.bot.username)
        await update.effective_chat.send_message(
            dummy_message, parse_mode=telegram.constants.ParseMode.HTML
        )
