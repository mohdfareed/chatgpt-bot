"""Command handlers for telegram command updates. It is responsible for parsing
updates and executing core module functionality."""

import abc
import inspect
import textwrap

import telegram
import telegram.ext as telegram_extensions
from typing_extensions import override

import chatgpt.core
import chatgpt.tools
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
    names = ("start", "help")
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


class Usage(Command):
    names = ("usage",)
    description = "Show the user and chat usage"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        usage = await utils.get_usage(message)
        await telegram_utils.reply_code(message, usage)


class DeleteMessage(Command):
    names = ("delete", "delete_message")
    description = "Delete a message from the chat history"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return
        try:
            await utils.delete_message(message.reply or message)
            await telegram_utils.reply_code(message, "Message deleted")
        except database.core.ModelNotFound:
            await telegram_utils.reply_code(message, "Message not found")


class SetSystemPrompt(Command):
    names = ("sys", "set_sys")
    description = "Set the system prompt of the model"

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        sys_message = None
        try:  # parse the message in the format `/command content`
            sys_message = message.text.split(" ", 1)[1].strip()
        except IndexError:
            pass

        # parse text from reply if no text was found in message
        if isinstance(message.reply, core.TextMessage):
            sys_message = sys_message or message.reply.text

        # use default prompt if no text was found
        sys_message = sys_message or chatgpt.core.ModelConfig().prompt.content
        await utils.set_prompt(message, sys_message)
        await telegram_utils.reply_code(
            message, f"System prompt updated successfully"
        )


class SetTemperature(Command):
    names: tuple = ("temp", "set_temp")
    description = "Set the model's temperature"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        try:  # parse the temperature from the message
            temp_str = message.text.split(" ", 1)[1].strip()
            # use default temp if no text was found
            temp_str = temp_str or chatgpt.core.ModelConfig().temperature
            temp = float(temp_str)
            if not 0.0 <= temp <= 2.0:
                raise ValueError
        except (IndexError, ValueError):
            await telegram_utils.reply_code(
                message, "Temperature must be between 0.0 and 2.0"
            )
            return

        await utils.set_temp(message, temp)
        await telegram_utils.reply_code(
            message, "Temperature set successfully"
        )
