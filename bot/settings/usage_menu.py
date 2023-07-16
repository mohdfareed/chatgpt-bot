"""Menu for displaying a user usage."""

from typing_extensions import override

from bot import core, metrics, utils


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
            f"<code>{user_metrics.usage / 1000}k tokens</code>\n"
            f"<code>${round(chat_metrics.usage_cost, 2)}</code>\n"
            f"<b>Chat tokens use and total cost of usage.</b>\n"
            f"<code>{chat_metrics.usage / 1000}k tokens</code>\n"
            f"<code>${round(chat_metrics.usage_cost, 2)}</code>"
        )
