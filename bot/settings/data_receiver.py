"""Menu for requesting and receiving data."""

import abc
import typing

import telegram
import telegram.constants
import telegram.ext as telegram_extensions
from typing_extensions import override

from bot import core, handlers, settings, utils

# the receivers of the active requests made by users
_active_requests: dict[int, "DataReceiver"] = {}
_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE


# class DataRequest(abc.ABC):
#     """A data request."""

#     def __init__(self, id: str, data_title: str, data_desc: str):
#         self.id = id
#         """The ID of the request."""
#         self.data_title = data_title
#         """The title of the data to be requested. Used as the button text."""
#         self.data_desc = data_desc
#         """The description of the data to be requested. Used as the menu content."""

#     @abc.abstractmethod
#     def data_handler(self, data_message: core.TelegramMessage) -> bool:
#         """The handler for the data. Returns whether the data was handled."""
#         ...


# class DataRequestButton(core.Button):
#     """A data request button. Requests data from the user."""

#     def __init__(self, request: DataRequest, parent: typing.Type[core.Menu]):
#         super().__init__(request.id, request.data_title)
#         self.request = request
#         """The data request details."""

#     @override
#     @classmethod
#     async def callback(cls, data, query):
#         if not query.message:
#             return
#         message = core.TelegramMessage(query.message)
#         # initialize request
#         _active_requests[query.from_user.id] = cls.request
#         await DataReceiverMenu(message, query.from_user.id).render()
#         await query.answer()


class DataReceiver(core.Menu, abc.ABC):
    """Menu shown when receiving data. Auto-closes when data is handled."""

    def __init__(self, message: core.TelegramMessage, user: telegram.User):
        """Initialize the menu."""
        super().__init__(message, user)
        self.has_error = False
        """Whether the receiver encountered an error handling data."""
        _active_requests[self.user.id] = self

    async def cancel(self):
        """Cancel the data request."""
        try:
            del _active_requests[self.user.id]
        except KeyError:
            pass
        await self.parent(self.message, self.user).render()

    @property
    @override
    async def info(self):
        return (
            f"{self.description}\n\n{self.error_info if self.has_error else ''}"
            "Only messages sent by "
        )

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
    def description(self) -> str:
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
        handlers.MessageHandler.filters & telegram_extensions.filters.TEXT
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
        receiver = _active_requests.get(query.from_user.id)

        if receiver:
            await receiver.cancel()
        await query.answer()
