"""Core types and classes."""

import abc
import inspect
import typing

import telegram
import telegram.ext as telegram_extensions
from typing_extensions import override

import chatgpt.messages
import database.core as database

_button = telegram.InlineKeyboardButton
_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE
_html_parse_mode = telegram.constants.ParseMode.HTML


class TelegramMessage:
    """Telegram message."""

    def __init__(self, message: telegram.Message):
        """Initialize a text message from a Telegram message."""
        message_user = message.from_user or message.sender_chat or message.chat

        self.id = message.message_id
        """The message ID."""
        self.topic_id: int | None = None
        """The topic ID if any."""
        self.chat = TelegramChat(message.chat)
        """The chat in which the message was sent."""
        self.user = TelegramUser(message_user)
        """The user who sent the message."""
        self.reply: TelegramMessage | None = None
        """The message to which this message is a reply if any."""
        self.telegram_message = message
        """The Telegram message instance."""

        # fill-in the topic if any
        if message.is_topic_message and message.message_thread_id:
            self.topic_id = message.message_thread_id
        # fill-in reply message if any
        if reply := message.reply_to_message:
            self.reply = TextMessage(reply)

    @property
    def chat_id(self) -> str:
        """The chat ID used by the chat model."""
        # user -1 as the topic ID if none (general chat)
        # topic ID's are always positive, thus this is unique
        return f"{self.chat.id}|{self.topic_id or -1}"

    @property
    def metadata(self) -> dict[str, str]:
        """The message metadata."""
        metadata = dict(
            id=str(self.id),
            username=self.user.username,
            reply_id=str(self.reply.id) if self.reply else None,
        )
        metadata = {k: v for k, v in metadata.items() if v is not None}
        return metadata


class TelegramChat:
    """Telegram chat."""

    def __init__(self, chat: telegram.Chat):
        """Initialize a chat from a Telegram chat."""
        self.id = chat.id
        """The chat ID."""
        self.title = chat.title or ""
        """The chat title if any."""
        self.telegram_chat = chat
        """The Telegram chat instance."""
        self._username = chat.username

    @property
    def username(self) -> str:
        """The chat's username. The chat title if no username."""
        return self._username or self.title


class TelegramUser:
    """Telegram user."""

    def __init__(self, user: telegram.User | telegram.Chat):
        """Initialize a user from a Telegram user."""
        self.id = user.id
        """The user ID."""
        self.first_name: str
        """The user first name if any."""
        self.last_name = user.last_name
        """The user last name if any."""
        self.telegram_user = user
        """The Telegram user or chat instance."""
        self._username = user.username

        # fill-in first name
        if isinstance(user, telegram.User):
            self.first_name = user.first_name
        else:  # first name for chats is the title
            self.first_name = TelegramChat(user).title

    @property
    def username(self) -> str:
        """The user's username. The user's fullname if no username."""
        return self._username or self.fullname

    @property
    def fullname(self) -> str:
        """The user's fullname."""
        first_last = f"{self.first_name} {self.last_name or ''}"
        return first_last.strip()


class TextMessage(TelegramMessage):
    """A Telegram text message."""

    def __init__(self, message: telegram.Message):
        super().__init__(message)
        self.text = message.text or message.caption or ""
        """The message text."""

    def to_chat_message(self):
        """Convert the message to a chat model message."""
        return chatgpt.messages.UserMessage(
            self.text, id=self.id, metadata=self.metadata
        )

    @classmethod
    def from_update(cls, update: telegram.Update):
        if not (update_message := update.effective_message):
            raise ValueError("Update has no message")
        if not update_message.text:
            raise ValueError("Update message has no text")
        return cls(update_message)


class Button(abc.ABC):
    """A button in a menu."""

    def __init__(self, data: str, button_text: str):
        self.data = data
        """The alphanumeric data of the callback."""
        self.button_text = button_text
        """The text for the button."""

    @property
    def telegram_button(self) -> telegram.InlineKeyboardButton:
        """The telegram button object."""
        callback_data = f"{type(self).button_id()}:{self.data}"
        return _button(self.button_text, callback_data=callback_data)

    @classmethod
    def button_id(cls) -> str:
        """The button ID."""
        return cls.__qualname__

    @classmethod
    def telegram_handler(cls) -> telegram_extensions.CallbackQueryHandler:
        """Create a telegram button handler for the button."""

        async def _handler(update: telegram.Update, _: _default_context):
            if not (query := update.callback_query):
                return  # only handle callback queries
            data = query.data.split(":", 1)[1]
            if inspect.iscoroutinefunction(cls.callback):
                await cls.callback(data, query)
            else:
                cls.callback(data, query)

        return telegram_extensions.CallbackQueryHandler(
            _handler, pattern=r"^{0}:.*$".format(cls.button_id())
        )

    @classmethod
    def all_handlers(cls) -> list[telegram_extensions.CallbackQueryHandler]:
        """Get every button's handler, recursively."""
        import bot.chat_handler
        import bot.settings

        handlers = []
        for button in cls.__subclasses__():
            # only add concrete buttons
            if not inspect.isabstract(button):
                handlers.append(button.telegram_handler())
            handlers.extend(button.all_handlers())
        return handlers

    @classmethod
    @abc.abstractmethod
    def callback(cls, data: str, query: telegram.CallbackQuery):
        """The callback for the button."""
        ...


class Menu(abc.ABC):
    """A menu displayed as a message."""

    def __init__(self, message: TelegramMessage, user: telegram.User):
        self.message = message
        """The message of the menu."""
        self.user = user
        """The user interacting with the menu."""

    @abc.abstractproperty
    async def info(self) -> str:
        """The menu's information. It is the content of the message."""
        ...

    @abc.abstractproperty
    async def layout(self) -> list[list[Button]]:
        """The menu's layout."""
        ...

    @staticmethod
    @abc.abstractmethod
    def title() -> str:
        """The menu's title."""
        ...

    async def render(self):
        """Render the menu."""
        import bot.telegram_utils

        menu_markup = bot.telegram_utils.create_markup(await self.layout)
        try:
            await self.message.telegram_message.edit_text(
                await self.info,
                reply_markup=menu_markup,
                parse_mode=_html_parse_mode,
            )
        except telegram.error.BadRequest as e:
            if "Message is not modified" in str(e):
                return  # ignore if the message was not modified
            else:  # raise if the error is not due to the message not changing
                raise e

    @classmethod
    def id(cls):
        return cls.__qualname__

    @classmethod
    def get_menu(cls, menu_id: str) -> typing.Type["Menu"] | None:
        """Get the menu with the given ID."""
        import bot.settings

        for menu in cls.__subclasses__():
            if menu.id() == menu_id:
                return menu
            # check if the menu has any submenus
            if submenu := menu.get_menu(menu_id):
                return submenu
        return None

    @staticmethod
    def create_grid(buttons: list[Button], back_button: "MenuButton | None"):
        grid = [buttons[n : n + 2] for n in range(0, len(buttons), 2)]
        if not back_button:
            return grid
        # if number of tools is even, new row for back button
        if len(buttons) % 2 == 0:
            grid.append([back_button])
        else:  # if number of tools is odd, add back button in the last row
            grid[-1] = [back_button, grid[-1][0]]
        return grid


class MenuButton(Button):
    """A button that displays a menu."""

    def __init__(self, menu: typing.Type[Menu], is_parent: bool = False):
        from bot.settings import BACK_BUTTON

        # add back button if parent
        title = f"{BACK_BUTTON} {menu.title()}" if is_parent else menu.title()
        super().__init__(menu.id(), title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = TelegramMessage(query.message)

        if not (menu := Menu.get_menu(data)):
            raise ValueError(f"Menu with ID {menu} not found.")
        await menu(message, query.from_user).render()
        await query.answer()
