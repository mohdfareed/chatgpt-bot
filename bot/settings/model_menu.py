"""Menu for setting the chat's model."""

from typing_extensions import override

import chatgpt.core
from bot import core, settings, utils


class ModelMenu(core.Menu):
    """Set the chat's model."""

    @property
    @override
    async def info(self):
        model = (await utils.get_config(self.message)).chat_model
        model_settings = (
            f"<b>The current configuration's chat model:</b>\n"
            f"Name: <code>{model.name}</code>\n"
            f"Size: <code>{model.size} tokens</code>\n"
            f"Input cost: <code>${model.input_cost}/1k tokens</code>\n"
            f"Output cost: <code>${model.output_cost}/1k tokens</code>\n\n"
            "Switch to another supported chat model."
        )
        return model_settings

    @property
    @override
    async def layout(self):
        from bot.settings.model_settings import ModelSettingsMenu

        model_buttons = []
        active_model = (await utils.get_config(self.message)).chat_model
        # create a button for each model
        for model in chatgpt.core.ModelConfig.supported_models():
            model_title = await self._create_model_title(model, active_model)
            model_buttons.append(ModelButton(model.name, model_title))
        # create the menu layout
        back_button = core.MenuButton(ModelSettingsMenu, is_parent=True)
        return ModelMenu.create_grid(model_buttons, back_button)

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

        # refresh the menu
        await ModelMenu(message, query.from_user).render()
        await query.answer()
