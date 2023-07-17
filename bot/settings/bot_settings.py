"""The main menu of the bot's settings. Acts as the entry point to configuring
the bot and the chat model."""

import telegram.constants
from typing_extensions import override

from bot import commands, core, metrics, settings, telegram_utils, utils
from bot.settings.config_menu import ConfigMenu
from bot.settings.model_settings import ModelSettingsMenu

_private = telegram.constants.ChatType.PRIVATE


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
        await telegram_utils.send_message(message, menu_info, menu_markup)
        await telegram_utils.delete_message(message)

    @property
    @override
    async def info(self):
        return "Configure the bot and model settings."

    @property
    @override
    async def layout(self) -> list[list[core.Button]]:
        chat = await metrics.TelegramMetrics(
            entity_id=self.message.chat_id
        ).load()
        will_reply = chat.reply_to_mentions
        reply_toggle_title = settings.create_title(
            "Reply to Mentions", will_reply, is_toggle=True
        )
        will_delete = chat.delete_messages
        deletion_toggle_title = settings.create_title(
            "Delete Messages", will_delete, is_toggle=True
        )

        if self.message.chat.telegram_chat.type == _private:
            return [
                [
                    core.MenuButton(ConfigMenu),
                    core.MenuButton(ModelSettingsMenu),
                ],
                [
                    DeleteHistoryButton(),
                    ToggleMessageDeletionButton(deletion_toggle_title),
                ],
                [CloseButton(), UsageButton()],
            ]
        # group chat menu
        return [
            [core.MenuButton(ConfigMenu), core.MenuButton(ModelSettingsMenu)],
            [DeleteHistoryButton()],
            [
                ToggleMessageDeletionButton(deletion_toggle_title),
                ToggleReplyModeButton(reply_toggle_title),
            ],
            [CloseButton(), UsageButton()],
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

        # delete model messages
        deleted_messages = await utils.delete_history(message)
        # delete telegram messages
        chat = await metrics.TelegramMetrics(entity_id=message.chat_id).load()
        if chat.delete_messages:
            for message_id in deleted_messages:
                await telegram_utils.delete_message(message, int(message_id))
        await query.answer("Chat history deleted")


class ToggleReplyModeButton(core.Button):
    """A button that toggles the reply mode of the bot."""

    def __init__(self, title):
        # use the title as the button data
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        if await utils.toggle_reply_mode(message.chat_id):
            await query.answer("Bot will reply to mentions only")
        else:
            await query.answer("Bot will reply to all messages")


class ToggleMessageDeletionButton(core.Button):
    """A button that toggles whether the bot deletes messages when clearing
    chat history."""

    def __init__(self, title):
        # use the title as the button data
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        if await utils.toggle_message_deletion(message.chat_id):
            await query.answer("Message deletion enabled")
        else:
            await query.answer("Message deletion disabled")


class UsageButton(core.Button):
    """A button that displays the usage."""

    def __init__(self):
        # use the title as the button data
        title = "$ Usage"
        super().__init__(title, title)

    @override
    @classmethod
    async def callback(cls, data, query):
        if not query.message:
            return
        message = core.TelegramMessage(query.message)

        user_usage, chat_usage = await utils.get_usage(
            query.from_user.id, message.chat_id
        )
        usage_info = cls._create_usage_message(user_usage, chat_usage)
        await query.answer(usage_info, show_alert=True)

    @classmethod
    def _create_usage_message(
        cls,
        user_metrics: metrics.TelegramMetrics,
        chat_metrics: metrics.TelegramMetrics,
    ) -> str:
        user_tokens = int(user_metrics.usage / 1000)
        chat_tokens = int(chat_metrics.usage / 1000)
        user_usage_cost = round(user_metrics.usage_cost, 2)
        chat_usage_cost = round(chat_metrics.usage_cost, 2)
        return (
            f"User usage:\n"
            f"{user_tokens}k tokens | ${user_usage_cost}\n"
            f"Chat usage:\n"
            f"{chat_tokens}k tokens | ${chat_usage_cost}"
        )


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
