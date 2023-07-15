"""Menu for setting the chat's model."""

from typing_extensions import override

import chatgpt.core
from bot import core, settings, utils
from bot.core import Menu, TelegramMessage


class ModelMenu(core.Menu):
    """Set the chat's model."""

    @property
    @override
    async def info(self):
        model = (await utils.get_config(self.message)).chat_model
        model_settings = (
            f"<b>The currently selected chat model:</b>\n"
            f"Name: <code>{model.title}</code>\n"
            f"Size: <code>{model.size} tokens</code>\n"
            f"Input cost: <code>${model.input_cost}/1k tokens</code>\n"
            f"Output cost: <code>${model.output_cost}/1k tokens</code>"
        )
        return model_settings

    @property
    @override
    async def layout(self):
        from bot.settings.main_menu import BotSettingsMenu

        active_model = (await utils.get_config(self.message)).chat_model
        buttons: list[list[core.Button]] = []
        for model in chatgpt.core.ModelConfig.supported_models():
            model_title = await self._create_model_title(model, active_model)
            buttons.append([ModelButton(model.name, model_title)])
        return buttons + [
            [core.MenuButton(BotSettingsMenu, is_parent=True)],
        ]

    @staticmethod
    @override
    def title():
        return "Chat Model"

    async def _create_model_title(
        self,
        model: chatgpt.core.SupportedChatModel,
        active_model: chatgpt.core.SupportedChatModel,
    ) -> str:
        return (
            f"{settings.ENABLED_INDICATOR} " if model == active_model else ""
        ) + model.title


class ModelButton(core.Button):
    """A button that sets a chat model."""

    def __init__(self, model_name: str, model_title: str):
        super().__init__(model_name, model_title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        # update the chat model
        config = await utils.get_config(message)
        config.chat_model = chatgpt.core.ModelConfig.model(data)
        await utils.set_config(message, config)

        await query.answer(f"Set chat model to {data}.")
        # refresh the menu
        await ModelMenu(message).render()
