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
from bot import core, formatter, handlers, telegram_utils, tools, utils

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
        import bot.config_menus

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


class Models(Command):
    names = ("models", "available_models")
    description = "Show the available models"

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        available_models = []
        for model in chatgpt.core.ModelConfig.supported_models():
            available_models.append(f"<code>{model.name}</code>")
        await message.telegram_message.reply_html(
            "\n".join(available_models).strip() or "No models available"
        )


class Tools(Command):
    names = ("tools", "available_tools")
    description = "Show the available tools"

    @override
    @staticmethod
    async def callback(update: telegram.Update, context: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        available_tools = []
        for tool in tools.available_tools():
            available_tools.append(f"<code>{tool.name}</code>")
        await message.telegram_message.reply_html(
            "\n".join(available_tools).strip() or "No tools available"
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


class DeleteHistory(Command):
    names = ("delete_history",)
    description = "Delete the chat history"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        await utils.delete_history(message)
        await telegram_utils.reply_code(message, "Chat history deleted")


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


class Model(Command):
    names: tuple = ("model",)
    description = "Get the chat model's configuration"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        config_text = await utils.load_config(message)
        await message.telegram_message.reply_html(config_text)


class SetModel(Command):
    names: tuple = ("set_model",)
    description = "Set the chat model"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        try:  # parse the model name from the message
            model_name = message.text.split(" ", 1)[1].strip()
            # use default model if no model name was found
            model_name = (
                model_name or chatgpt.core.ModelConfig().chat_model.name
            )
            model = chatgpt.core.ModelConfig.model(model_name)
        except (IndexError, ValueError):
            await telegram_utils.reply_code(message, "Invalid model name")
            return

        await utils.set_model(message, model.name)
        await telegram_utils.reply_code(message, "Model set successfully")


class SetTools(Command):
    names: tuple = ("set_tools",)
    description = "Set the model's tools, separated by spaces or newlines"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        # use default tools if no tools are found
        selected_tools = chatgpt.core.ModelConfig().tools
        try:  # parse the tool names from the message
            requested_tools = message.text.split(" ", 1)[1].strip()
            for tool in requested_tools.split():
                try:  # check if the tool is valid
                    selected_tool = tools.from_tool_name(tool)
                except ValueError:  # stop if the tool is invalid
                    await telegram_utils.reply_code(
                        message, f"Invalid tool: {tool}"
                    )
                    return
                selected_tools.append(selected_tool)
        except IndexError:
            pass  # use default tools if no tools were provided

        await utils.set_tools(message, selected_tools)
        await telegram_utils.reply_code(message, "Tools set successfully")


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


class ToggleStreaming(Command):
    names: tuple = ("stream", "toggle_stream")
    description = "Toggle whether the model streams messages"

    @override
    @staticmethod
    async def callback(update: telegram.Update, _: _default_context):
        try:  # check if text message was sent
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        if await utils.toggle_streaming(message):
            await telegram_utils.reply_code(message, "Streaming enabled")
        else:
            await telegram_utils.reply_code(message, "Streaming disabled")
