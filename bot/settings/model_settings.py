"""An organizational menu of the chat model's settings."""

from typing_extensions import override

from bot import core, settings, utils
from bot.settings.data_receivers import DataReceiver
from bot.settings.model_menu import ModelMenu
from bot.settings.tools_menu import ToolsMenu


class ModelSettingsMenu(core.Menu):
    """The main menu of the model's settings."""

    @property
    @override
    async def info(self):
        return "Modify the active model's configuration."

    @property
    @override
    async def layout(self):
        from bot.settings.bot_settings import BotSettingsMenu

        config = await utils.get_config(self.message)
        stream_toggle_title = settings.create_title(
            "Stream Messages", config.streaming, is_toggle=True
        )

        return [
            [core.MenuButton(ModelMenu), core.MenuButton(ToolsMenu)],
            [
                core.MenuButton(SysPromptReceiver, icon="✎ "),
                core.MenuButton(TemperatureReceiver, icon="✎ "),
            ],
            [
                core.MenuButton(BotSettingsMenu, is_parent=True),
                ToggleStreamingButton(stream_toggle_title),
            ],
        ]

    @staticmethod
    @override
    def title():
        return "Active Model"


class SysPromptReceiver(DataReceiver):
    """Data receiver for the chat model's system prompt."""

    @property
    @override
    def parent(self):
        return ModelSettingsMenu

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
        return ModelSettingsMenu

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


class ToggleStreamingButton(core.Button):
    """A button that toggles streaming of replies."""

    def __init__(self, title):
        # use the title as the button data
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        await utils.toggle_streaming(message)
        # refresh the menu
        await ModelSettingsMenu(message, query.from_user).render()
        await query.answer()
