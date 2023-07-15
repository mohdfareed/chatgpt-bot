"""Menu for setting th bot's tools."""


from typing_extensions import override

import chatgpt.tools
from bot import core, settings, tools, utils


class ToolsMenu(core.Menu):
    """Set the model's tools."""

    @property
    @override
    async def info(self):
        return "Toggle tools for the chat model to use."

    @property
    @override
    async def layout(self):
        from bot.settings.main_menu import BotSettingsMenu

        buttons: list[list[core.Button]] = []
        for tool in tools.available_tools():
            tool_title = await self._create_tool_title(tool)
            buttons.append([ToolButton(tool.name, tool_title)])

        return buttons + [
            [core.MenuButton(BotSettingsMenu, is_parent=True)],
        ]

    @staticmethod
    @override
    def title():
        return "Model Tools"

    async def _create_tool_title(self, tool: chatgpt.tools.Tool) -> str:
        has_tool = await utils.has_tool(self.message, tool)
        return (
            f"{settings.ENABLED_INDICATOR} " if has_tool else ""
        ) + tool.title


class ToolButton(core.Button):
    """A button that enables a tool."""

    def __init__(self, tool_name: str, tool_title: str):
        super().__init__(tool_name, tool_title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)
        # toggle the tool
        tool = tools.from_tool_name(data)
        await utils.toggle_tool(message, tool)
        # refresh the menu
        await ToolsMenu(message).render()
        await query.answer()
