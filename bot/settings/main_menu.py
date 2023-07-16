"""The main menu of the bot's settings. Acts as the entry point to configuring
the bot and the chat model."""

from typing_extensions import override

from bot import commands, core, settings, telegram_utils, utils
from bot.settings.data_receiver import DataReceiver


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
        return "Configure the bot and chat model settings."

    @property
    @override
    async def layout(self) -> list[list[core.Button]]:
        from bot.settings.config_menu import ConfigMenu
        from bot.settings.data_receiver import DataReceiver
        from bot.settings.model_menu import ModelMenu
        from bot.settings.tools_menu import ToolsMenu
        from bot.settings.usage_menu import UsageMenu

        return [
            [core.MenuButton(ConfigMenu)],
            [
                core.MenuButton(ModelMenu),
                core.MenuButton(ToolsMenu),
            ],
            [
                core.MenuButton(SysPromptReceiver),
                core.MenuButton(TemperatureReceiver),
            ],
            [
                DeleteHistoryButton(),
                ToggleStreamingButton(),
            ],
            [CloseButton(), core.MenuButton(UsageMenu)],
        ]

    @staticmethod
    @override
    def title():
        return "Settings"


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


class SysPromptReceiver(DataReceiver):
    """Data receiver for the chat model's system prompt."""

    @property
    @override
    def parent(self):
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
