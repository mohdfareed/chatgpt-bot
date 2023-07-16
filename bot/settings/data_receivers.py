"""Menu for requesting and receiving data."""

import abc
import typing

import telegram
import telegram.constants
import telegram.ext as telegram_extensions
from typing_extensions import override

from bot import core, handlers, settings, utils

# the receivers of the active requests
_active_requests: dict[str, "DataReceiver"] = {}
_private_chat = telegram.Chat.PRIVATE


class DataReceiver(core.Menu, abc.ABC):
    """Menu shown when receiving data. Auto-closes when data is handled."""

    def __init__(self, message: core.TelegramMessage, user: telegram.User):
        """Initialize the menu."""
        super().__init__(message, user)
        self.has_error = False
        """Whether the receiver encountered an error handling data."""
        _active_requests[id(self.message)] = self

    async def close(self):
        """Cancel the data request."""
        try:
            del _active_requests[id(self.message)]
        except KeyError:
            pass

    async def handle(self, data_message: core.TelegramMessage):
        """Handle the data."""
        if not await self.data_handler(data_message):
            self.has_error = True
        else:
            self.has_error = False
        await self.render()

    @property
    @override
    async def info(self):
        message = await self.description + "\n\n"
        if self.has_error:
            message += self.error_info + "\n\n"
        if self.message.chat.telegram_chat.type != _private_chat:
            message += f"Reply must be by {self.user.name}."
        return message.strip()

    @property
    @override
    async def layout(self):
        return [
            [RequestCancelButton(self.parent)],
        ]

    @property
    @abc.abstractmethod
    def parent(self) -> typing.Type[core.Menu]:
        """The parent menu."""
        ...

    @property
    @abc.abstractmethod
    async def description(self) -> str:
        """The description of the data to be requested."""
        ...

    @property
    @abc.abstractmethod
    def error_info(self) -> str:
        """The error information to be displayed on invalid data."""
        ...

    @abc.abstractmethod
    async def data_handler(self, data_message: core.TelegramMessage) -> bool:
        """The handler for the data. Returns whether the data was handled."""
        ...


class TextDataHandler(handlers.MessageHandler):
    """Handle a text input message to a data request."""

    filters = (
        handlers.MessageHandler.filters
        & telegram_extensions.filters.TEXT
        & telegram_extensions.filters.REPLY
    )
    block = True
    group = 0

    @override
    @staticmethod
    async def callback(update, context):
        try:  # check if text message
            message = core.TextMessage.from_update(update)
        except ValueError:
            return

        # retrieve receiver
        receiver = _active_requests.get(id(message.reply))
        if not receiver:
            return

        await receiver.handle(message)
        try:  # delete data after handling
            await message.telegram_message.delete()
        except:
            pass

        # don't pass to other handlers
        raise telegram_extensions.ApplicationHandlerStop


class RequestCancelButton(core.MenuButton):
    """Button for cancelling a data request."""

    def __init__(self, parent_menu: typing.Type[core.Menu]):
        super().__init__(parent_menu, is_parent=True)
        self.button_text = f"{settings.BACK_BUTTON} Cancel"

    @override
    @classmethod
    async def callback(cls, _, query: telegram.CallbackQuery):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)
        receiver = _active_requests.get(id(message))
        if receiver:
            await receiver.close()
        await super().callback(_, query)


class SysPromptReceiver(DataReceiver):
    """Data receiver for the chat model's system prompt."""

    @property
    @override
    def parent(self):
        from bot.settings.main_menu import BotSettingsMenu

        return BotSettingsMenu

    @property
    @override
    async def description(self):
        prompt = (await utils.get_config(self.message)).prompt
        prompt_text = prompt.content if prompt else "No system prompt is set."
        return (
            f"<b>The current configuration's system prompt: \n</b>"
            f"<code>{prompt_text}</code>\n\n"
            "Reply with the a new system prompt to set it."
        )

    @property
    @override
    def error_info(self):
        return "<b>Error:</b> <code>Invalid system prompt provided...</code>"

    @override
    async def data_handler(self, data_message: core.TextMessage):
        try:
            await utils.set_prompt(self.message, data_message.text)
        except ValueError:
            return False
        return True

    @staticmethod
    @override
    def title():
        return "System Prompt"


class TemperatureReceiver(DataReceiver):
    """Data receiver for the chat model's temperature setting."""

    @property
    @override
    def parent(self):
        from bot.settings.main_menu import BotSettingsMenu

        return BotSettingsMenu

    @property
    @override
    async def description(self):
        temp = (await utils.get_config(self.message)).temperature
        return (
            f"<b>The current configuration's temperature: </b>"
            f"<code>{round(temp, 2)}</code>\n"
            "Reply with a value between in <code>[0.0, 2.0]</code> to set it."
        )

    @property
    @override
    def error_info(self):
        return "<b>Error:</b> <code>Invalid value provided...</code>"

    @override
    async def data_handler(self, data_message: core.TextMessage):
        try:
            temperature = float(data_message.text)
            await utils.set_temp(self.message, temperature)
        except ValueError:
            return False
        return True

    @staticmethod
    @override
    def title():
        return "Temperature"


def id(message: core.TelegramMessage | None) -> str:
    """Get the ID of a user in a chat."""
    return f"{message.chat_id}:{message.id}" if message else ""
