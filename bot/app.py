"""The ChatGPT Telegram bot application. This module contains the bot's entry
point. It manages the bot's lifecycle and tunneling updates to handlers."""

import asyncio
import logging
import secrets

import telegram
import telegram.ext as telegram_extensions

import bot
from bot import commands, core, handlers

BOT_NAME = "ChatGPT@Dev" if bot.dev_mode else "ChatGPT"
SHORT_DESCRIPTION = "ChatGPT bot"
DESCRIPTION = """
ChatGPT based Telegram bot.
""".strip()

active_bot: telegram_extensions.ExtBot
"""The active bot instance."""


def run(update_profile=True):
    """Setup and run the bot."""
    global active_bot

    # configure the bot
    defaults = telegram_extensions.Defaults(
        parse_mode=telegram.constants.ParseMode.HTML,
        allow_sending_without_reply=True,
        quote=True,
        block=False,
    )

    # setup the application
    application = (
        telegram_extensions.Application.builder()
        .token(bot.token)
        .rate_limiter(telegram_extensions.AIORateLimiter())
        .defaults(defaults)
        .build()
    )

    active_bot = application.bot
    # setup the bot's updates handlers
    setup_handlers(application)
    # update the bot's profile, if specified
    setup_profile() if update_profile else None

    # start the bot
    if not bot.dev_mode:  # run in webhook mode for production
        webhook_str = f"{bot.webhook} [{bot.webhook_addr}:{bot.webhook_port}]"
        bot.logger.info(f"Using webhook: {webhook_str}")

        application.run_webhook(
            listen=bot.webhook_addr,
            port=bot.webhook_port,
            webhook_url=bot.webhook,
            secret_token=secrets.token_hex(32),
            drop_pending_updates=True
        )
    else:  # run in polling mode for development
        bot.logger.warning("Running in development mode")
        application.run_polling(drop_pending_updates=True)


def setup_profile():
    # disable logging for the profile setup
    error_module = "telegram.ext.AIORateLimiter"
    prev_level = logging.getLogger(error_module).level

    try:  # profile setup has a very long cool-down
        logging.getLogger(error_module).setLevel(logging.CRITICAL)
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        _ = new_loop.run_until_complete(_setup_profile())
        # restore the previous logging level
        logging.getLogger(error_module).setLevel(prev_level)
        bot.logger.info("Bot profile set successfully")
    except Exception:
        bot.logger.warning("Bot profile could not be set")


def setup_handlers(app: telegram_extensions.Application):
    app.add_error_handler(_error_handler)
    for button_handler in core.Button.all_handlers():
        app.add_handler(button_handler)
    for command in commands.Command.all_commands():
        app.add_handler(command.handler, command.group)
    for handler in handlers.MessageHandler.all_handlers():
        app.add_handler(handler.handler, handler.group)


async def _error_handler(update, context: telegram_extensions.CallbackContext):
    import bot.formatter
    import bot.telegram_utils

    if (  # ignore old queries
        "Query is too old and response timeout expired or query id is invalid"
        in str(context.error)
    ):
        return

    # reply with the error message if possible
    if isinstance(update, telegram.Update) and update.effective_message:
        message = core.TelegramMessage(update.effective_message)
        error = bot.formatter.format_message(str(context.error))
        await bot.telegram_utils.reply_code(message, error)
    # re-raise the error to be logged
    raise context.error or Exception("Unknown error encountered...")


async def _setup_profile():
    global active_bot

    cmds = [cmd.bot_command for cmd in commands.Command.all_commands()]
    # await active_bot.set_my_name(BOT_NAME)
    await active_bot.set_my_description(DESCRIPTION)
    await active_bot.set_my_short_description(SHORT_DESCRIPTION)
    await active_bot.set_my_commands(cmds)
    await active_bot.set_my_default_administrator_rights(
        telegram.ChatAdministratorRights(
            can_delete_messages=True,
            can_manage_topics=True,
            # required arguments
            is_anonymous=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            # optional arguments
            can_post_messages=False,
            can_edit_messages=False,
            can_pin_messages=False,
        )
    )
