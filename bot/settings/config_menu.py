"""The model configuration selector."""

from typing_extensions import override

import chatgpt.core
import chatgpt.messages
from bot import core, metrics, settings, utils


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
            "<b>Active model configuration:</b>\n"
            f"Model: <code>{config.chat_model.title}</code>\n"
            f"Temperature: <code>{round(config.temperature, 2)}</code>\n"
            f"Streaming: <code>{config.streaming}</code>\n"
            f"Tools: {', '.join(tools_titles)}\n"
            f"System prompt: <code>{prompt.content}</code>\n\n"
            "The active configuration is chat specific; while the list of "
            "available configurations is user specific. Modifications to "
            "the configurations list will be applied towards the user "
            "requesting the change.\n\n"
            "Select a model configuration to activate it."
        )

    @property
    @override
    async def layout(self):
        from bot.settings.bot_settings import BotSettingsMenu

        config_buttons = []
        active_config = await utils.get_config(self.message)
        configs = await metrics.TelegramMetrics.get_configs(str(self.user.id))
        # create a button for each config
        for config, index in zip(configs, range(len(configs))):
            config_title = settings.create_title(
                f"Config {index + 1}", config == active_config, is_toggle=False
            )
            config_buttons.append(SetConfigButton(index, config_title))
        # create the menu layout
        menu = ConfigMenu.create_grid(config_buttons, None)
        # add back and control buttons
        menu.append([AddConfigButton(), DeleteConfigButton()])
        menu.append([core.MenuButton(BotSettingsMenu, is_parent=True)])
        return menu

    @staticmethod
    @override
    def title():
        return "Configurations"


class SetConfigButton(core.Button):
    """A button that sets a model configuration."""

    def __init__(self, config_index: int, title: str):
        # use config name as button data
        super().__init__(str(config_index), title)

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
        await query.answer(f"Model configuration {data} activated")
        # refresh the menu
        await ConfigMenu(message, query.from_user).render()


class DeleteConfigButton(core.Button):
    """A button that deletes a model configuration."""

    def __init__(self):
        # use title name as button data
        title = "Delete"
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
            await query.answer(f"Model configuration deleted")
            # refresh the menu
            await ConfigMenu(message, query.from_user).render()
        else:
            await query.answer(f"Model configuration not found")


class AddConfigButton(core.Button):
    """A button that adds a model configuration to the user."""

    def __init__(self):
        # use title name as button data
        title = "Add"
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
            await query.answer(f"Model configuration added")
        else:
            await query.answer(f"Model configuration already exists")
        # refresh the menu
        await ConfigMenu(message, query.from_user).render()
