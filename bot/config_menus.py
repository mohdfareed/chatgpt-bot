"""The inline keyboard for the configuration menu of the model and bot."""

import asyncio
import typing

import telegram
from typing_extensions import override

import chatgpt.core
from bot import commands, core, telegram_utils, utils
from bot.core import TelegramMessage

BACK_BUTTON = "⬅ Back"


class BotSettingsMenu(core.Menu, commands.Command):
    """The main menu of the bot's settings. Acts as the entry point to
    configuring the bot and the chat model."""

    def __init__(self, message: TelegramMessage | None = None) -> None:
        # initialize as root menu if no message is given
        super().__init__(message)  # type: ignore

    names = ("settings",)
    description = "Configure the bot and chat model."

    @staticmethod
    @override
    async def callback(update, context):
        if not update.effective_message:
            return

        message = core.TelegramMessage(update.effective_message)
        menu = BotSettingsMenu(message)
        menu_markup = telegram_utils.create_markup(await menu.layout)
        menu_info = await menu.info  # type: ignore
        await telegram_utils.send_message(message, menu_info, menu_markup)

    @property
    @override
    async def info(self):
        await asyncio.sleep(0.1)
        return "Configure the bot and chat model settings."

    @property
    @override
    async def layout(self) -> list[list[core.Button]]:
        return [
            [
                MenuButton(ModelMenu, "Chat Model"),
            ],
            [
                CloseButton("Close Menu"),
            ],
        ]


class ModelMenu(core.Menu):
    """Set the chat's model."""

    class ModelButton(core.Button):
        """A button that sets a chat model."""

        def __init__(self, chat_model: str, title: str):
            # use chat model name as button data
            super().__init__(chat_model, title)

        @override
        @classmethod
        async def callback(cls, data, query):
            """The callback for the button."""
            if not query.message:
                return
            message = core.TelegramMessage(query.message)
            await utils.set_model(message, data)
            await query.answer(f"Set chat model to {data}.")
            # refresh the menu
            await ModelMenu(message).render()

    @property
    @override
    async def info(self):
        model = await utils.get_model(self.message)
        model_settings = (
            f"The currently selected chat model:\n"
            f"Name: <code>{model.title}</code>\n"
            f"Size: <code>{model.size} tokens</code>\n"
            f"Input cost: <code>${model.input_cost}/1k tokens</code>\n"
            f"Output cost: <code>${model.output_cost}/1k tokens</code>"
        )
        return model_settings

    @property
    @override
    async def layout(self):
        models = []
        for model in chatgpt.core.ModelConfig.supported_models():
            models.append(
                [ModelMenu.ModelButton(model.name, f"{model.title}")]
            )
        return models + [
            [MenuButton(BotSettingsMenu, BACK_BUTTON
        )]]


class MenuButton(core.Button):
    """A button that displays a menu."""

    def __init__(self, menu: typing.Type[core.Menu], title: str):
        # use menu id as button data
        super().__init__(menu.menu_id(), title)

    @override
    @classmethod
    async def callback(cls, data, query):
        """The callback for the button."""
        if not query.message:
            return
        if not (menu := core.Menu.get_menu(data)):
            raise ValueError(f"Menu with ID {data} not found.")
        await menu(core.TelegramMessage(query.message)).render()


class CloseButton(core.Button):
    """A button that closes the menu."""

    def __init__(self, title: str):
        # use menu id as button data
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        """The callback for the button."""
        if not query.message:
            return
        await query.message.delete()
