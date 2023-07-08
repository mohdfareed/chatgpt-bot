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


class HelpCommand(Command):
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
        dummy_message = formatter.md_html(HelpCommand.help_message)
        dummy_message = dummy_message.format(bot=context.bot.username)
        await update.effective_chat.send_message(
            dummy_message, parse_mode=telegram.constants.ParseMode.HTML
        )


class UsageCommand(Command):
    names = ("usage",)
    description = "Show the user and chat usage"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        db_user = await bot.models.TelegramMetrics(
            model_id=str(message.user.id)
        ).load()
        db_chat = await bot.models.TelegramMetrics(
            model_id=message.chat_id
        ).load()

        usage = (
            f"User usage: ${round(db_user.usage, 4)}\n"
            f"    tokens: {db_user.usage_cost}\n"
            f"Chat usage: ${round(db_chat.usage, 4)}\n"
            f"    tokens: {db_chat.usage_cost}"
        )
        await utils.reply_code(update_message, usage)


class DeleteHistoryCommand(Command):
    names = ("delete_history", "delete")
    description = "Delete the chat history"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        chat_history = await memory.ChatHistory.initialize(message.chat_id)
        await chat_history.clear()
        await utils.reply_code(update_message, "Chat history deleted")


class PromptCommand(Command):
    names = ("edit_sys", "edit")
    description = "Edit the system prompt"

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
                update_message, f"No text found in message or reply"
            )
            return

        # create new system message
        await utils.save_prompt(message, sys_message)
        await utils.reply_code(
            update_message, f"System prompt updated successfully"
        )


class GetSystemPrompt(Command):
    names: tuple = ("get_sys", "sys")
    description = "Get the system prompt"

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        if not (update_message := update.effective_message):
            return

        message = bot.models.TextMessage(update_message)
        text = (
            await utils.load_prompt(message)
        ).content or "No system prompt exists"
        await utils.reply_code(update_message, text)


def all_commands(command=Command):
    """All available bot commands.
    Recursively yields all concrete subclasses of the base class."""
    if not inspect.isabstract(command):
        yield command()  # type: ignore
    for subcommand in command.__subclasses__():
        yield from all_commands(subcommand)
