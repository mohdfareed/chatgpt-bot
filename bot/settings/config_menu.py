"""The model configuration selector."""

from typing_extensions import override

import chatgpt.messages
from bot import core, metrics, utils


class ConfigMenu(core.Menu):
    """Choose a model configuration."""

    @property
    @override
    async def info(self):
        config = await utils.get_config(self.message)
        tools = await utils.get_tools(self.message)
        tools_titles = [tool.title for tool in tools]
        prompt = config.prompt or chatgpt.messages.SystemMessage("")
        return (
            "Active model configuration:\n"
            f"Model: <code>{config.chat_model.title}</code>\n"
            f"Temperature: <code>{config.temperature}</code>\n"
            f"Streams messages: <code>{config.streaming}</code>\n"
            f"Tools: {', '.join(tools_titles)}\n"
            f"System prompt: <code>{prompt.content}</code>"
        )

    @property
    @override
    async def layout(self):
        from bot.settings.main_menu import BotSettingsMenu

        configs = await metrics.TelegramMetrics.get_configs(
            str(self.message.chat_id)
        )

        buttons: list[list[core.Button]] = [
            [SetConfigButton(index)] for index in range(len(configs))
        ]
        return buttons + [
            [AddConfigButton(), DeleteConfigButton()],
            [core.MenuButton(BotSettingsMenu, is_parent=True)],
        ]

    @staticmethod
    @override
    def title():
        return "Configurations"


class SetConfigButton(core.Button):
    """A button that sets a model configuration."""

    def __init__(self, config_index: int):
        # use config name as button data
        super().__init__(str(config_index), f"Config {config_index}")

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)
        configs = await metrics.TelegramMetrics.get_configs(
            str(query.from_user.id)
        )

        await utils.set_config(message, configs[int(data)])
        await query.answer(f"Activate model configuration {data}.")
        # refresh the menu
        await ConfigMenu(message).render()


class DeleteConfigButton(core.Button):
    """A button that deletes a model configuration."""

    def __init__(self):
        # use title name as button data
        title = "Add Current Configuration"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)
        active_config = await utils.get_config(message)

        if await metrics.TelegramMetrics.delete_config(
            str(query.from_user.id), active_config
        ):
            await query.answer(f"Model configuration deleted.")
            await ConfigMenu(message).render()  # refresh the menu
        else:
            await query.answer(f"Model active configuration not found.")


class AddConfigButton(core.Button):
    """A button that adds a model configuration to the user."""

    def __init__(self):
        # use title name as button data
        title = "Add Current Configuration"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)
        config = await utils.get_config(message)

        if await metrics.TelegramMetrics.add_config(
            str(query.from_user.id), config
        ):
            await query.answer(f"Model configuration added.")
        else:
            await query.answer(f"Model configuration already exists.")
        # refresh the menu
        await ConfigMenu(message).render()
