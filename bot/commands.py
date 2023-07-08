"""Command handlers for telegram command updates. It is responsible for parsing
updates and executing core module functionality."""

import abc
import inspect
import textwrap

import telegram
import telegram.ext as telegram_extensions
from typing_extensions import override

import bot.models
from bot import formatter, handlers, utils
from chatgpt import memory
from chatgpt.openai import supported_models

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
            callback=type(self).callback,
            filters=type(self).filters,
        )
        # set blocking if specified, use default otherwise
        if self.block is not None:
            handler.block = self.block
        return handler

    @property
    def bot_command(self) -> telegram.BotCommand:
        return telegram.BotCommand(self.names[0], self.description)


class Help(Command):
    names = ("start", "help")
    description = "Show the help message"

    help_message = textwrap.dedent(
        """
        The bot takes into context all messages sent in the chat, responding \
        only to messages that mention it.
        Set the system prompt by replying to a message with the command:
        ```
        /edit_sys@{bot}
        ```

        The text of the message to which you reply will be used as the prompt.
        You can also pass the text of the prompt directly to the command:
        ```
        /edit_sys@{bot} The text of the prompt.
        ```
        """
    ).strip()

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        dummy_message = formatter.md_html(Help.help_message)
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
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        usage = await utils.get_usage(message)
        await utils.reply_code(message, usage)


class DeleteHistory(Command):
    names = ("delete_history",)
    description = "Delete the chat history"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        chat_history = await memory.ChatHistory.initialize(message.chat_id)
        await chat_history.clear()
        await utils.reply_code(message, "Chat history deleted")


class DeleteMessage(Command):
    names = ("delete", "delete_message")
    description = "Delete a message from the chat history"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return
        message = bot.models.TextMessage(update_message)
        chat_history = await memory.ChatHistory.initialize(message.chat_id)
        await chat_history.remove_message(str(message.reply.id))
        await utils.reply_code(message, "Message deleted")


class Model(Command):
    names: tuple = ("model",)
    description = "Get the chat model's configuration"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        config_text = await utils.load_config(message)
        await utils.reply_code(message, config_text)


class SetModel(Command):
    names: tuple = ("set_model",)
    description = "Set the chat model"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        try:  # parse the model name from the message
            model_name = message.text.split(" ", 1)[1].strip()
            model = supported_models.chat_model(model_name)
        except (IndexError, ValueError):
            await utils.reply_code(message, "Invalid model name")
            return

        await utils.set_model(message, model.name)
        await utils.reply_code(message, "Model set successfully")


class SetSystemPrompt(Command):
    names = ("sys", "set_sys")
    description = "Set the system prompt of the model"

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        if not (update_message := update.effective_message):
            return
        message = bot.models.TextMessage(update_message)

        sys_message = None
        try:  # parse the message in the format `/command content`
            sys_message = message.text.split(" ", 1)[1].strip()
        except IndexError:
            pass

        # parse text from reply if no text was found in message
        if isinstance(message.reply, bot.models.TextMessage):
            sys_message = sys_message or message.reply.text

        if not sys_message:  # no text found
            await utils.reply_code(
                message, f"No text found in message or reply"
            )
            return

        # create new system message
        await utils.set_prompt(message, sys_message)
        await utils.reply_code(message, f"System prompt updated successfully")


class SetTemperature(Command):
    names: tuple = ("temp", "set_temp")
    description = "Set the model's temperature"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        try:  # parse the temperature from the message
            temp_str = message.text.split(" ", 1)[1].strip()
            temp = float(temp_str)
            if not 0.0 <= temp <= 2.0:
                raise ValueError
        except (IndexError, ValueError):
            await utils.reply_code(
                message, "Temperature must be between 0.0 and 2.0"
            )
            return

        await utils.set_temp(message, temp)
        await utils.reply_code(message, "Temperature set successfully")


class ToggleStreaming(Command):
    names: tuple = ("stream", "toggle_stream")
    description = "Toggle whether the model streams messages"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        if await utils.toggle_streaming(message):
            await utils.reply_code(message, "Streaming enabled")
        else:
            await utils.reply_code(message, "Streaming disabled")


class Stop(Command):
    names: tuple = ("stop",)
    description = "Stop the model from generating the message"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        if message.reply:
            await utils.stop_model(message)
            await utils.reply_code(message.reply, "Model stopped")
        else:
            await utils.stop_model(message, stop_all=True)
            await utils.reply_code(message, "All models stopped")


def all_commands(command=Command):
    """All available bot commands.
    Recursively yields all concrete subclasses of the base class."""
    if not inspect.isabstract(command):
        yield command()  # type: ignore
    for subcommand in command.__subclasses__():
        yield from all_commands(subcommand)
