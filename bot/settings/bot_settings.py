"""The main menu of the bot's settings. Acts as the entry point to configuring
the bot and the chat model."""

from typing_extensions import override

from bot import commands, core, metrics, settings, telegram_utils, utils
from bot.settings.config_menu import ConfigMenu
from bot.settings.model_settings import ModelSettingsMenu


class BotSettingsMenu(core.Menu, commands.Command):
    """The main menu of the bot's settings. Acts as the entry point to
    configuring the bot and the chat model."""

    def __init__(
        self,
        message: core.TelegramMessage | None = None,
        user_id: int | None = None,
    ) -> None:
        # initialize as root menu if no message is given
        super().__init__(message, user_id)  # type: ignore

    names = ("start", "settings")
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
        await telegram_utils.delete_message(message)
        await telegram_utils.send_message(message, menu_info, menu_markup)

    @property
    @override
    async def info(self):
        return "Configure the bot and model settings."

    @property
    @override
    async def layout(self) -> list[list[core.Button]]:
        return [
            [core.MenuButton(ConfigMenu), core.MenuButton(ModelSettingsMenu)],
            [DeleteHistoryButton(), ToggleStreamingButton()],
            [CloseButton(), core.MenuButton(UsageMenu)],
        ]

    @staticmethod
    @override
    def title():
        return "Settings"


class UsageMenu(core.Menu):
    """Show the user's usage of the bot."""

    @property
    @override
    async def info(self):
        user_usage, chat_usage = await utils.get_usage(
            self.user.id or self.message.user.id, self.message.chat_id
        )
        usage_info = self._create_usage_message(user_usage, chat_usage)
        return usage_info

    @property
    @override
    async def layout(self):
        from bot.settings.bot_settings import BotSettingsMenu

        return [
            [core.MenuButton(BotSettingsMenu, is_parent=True)],
        ]

    @staticmethod
    @override
    def title():
        return "$ Usage"

    def _create_usage_message(
        self,
        user_metrics: metrics.TelegramMetrics,
        chat_metrics: metrics.TelegramMetrics,
    ) -> str:
        return (
            f"<b>User tokens use and total cost of usage.</b>\n"
            f"<code>{int(user_metrics.usage / 1000)}k tokens</code>\n"
            f"<code>${round(chat_metrics.usage_cost, 2)}</code>\n"
            f"<b>Chat tokens use and total cost of usage.</b>\n"
            f"<code>{int(chat_metrics.usage / 1000)}k tokens</code>\n"
            f"<code>${round(chat_metrics.usage_cost, 2)}</code>"
        )


class DeleteHistoryButton(core.Button):
    """A button that deletes the chat history."""

    def __init__(self):
        # use the title as the button data
        title = "Delete History"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        await utils.delete_history(message)
        await query.answer("Chat history deleted")


class ToggleStreamingButton(core.Button):
    """A button that toggles streaming of replies."""

    def __init__(self):
        # use the title as the button data
        title = "Toggle Streaming"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        if await utils.toggle_streaming(message):
            await query.answer("Streaming enabled")
        else:
            await query.answer("Streaming disabled")


class CloseButton(core.Button):
    """A button that closes the menu."""

    def __init__(self):
        # use title as button data
        title = f"{settings.DISABLED_INDICATOR} Close"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        await query.message.delete()
        await query.answer()
