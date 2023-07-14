"""The ChatGPT Telegram bot application. This module contains the bot's entry
point. It manages the bot's lifecycle and tunneling updates to handlers."""

import asyncio
import logging
import secrets

import telegram
import telegram.ext as telegram_extensions

import bot
from bot import commands, config_menus, core, handlers


def run():
    """Setup and run the bot."""

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

    # setup the bot's application
    setup_handlers(application)
    setup_profile(application)

    # start the bot
    if not bot.dev_mode:  # run in webhook mode for production
        webhook_str = f"{bot.webhook} [{bot.webhook_addr}:{bot.webhook_port}]"
        bot.logger.info(f"Using webhook: {webhook_str}")

        application.run_webhook(
            listen=bot.webhook_addr,
            port=bot.webhook_port,
            webhook_url=bot.webhook,
            secret_token=secrets.token_hex(32),
        )
    else:  # run in polling mode for development
        bot.logger.warning("Running in development mode")
        application.run_polling()
    bot.logger.info("Telegram bot has stopped")


def setup_profile(app: telegram_extensions.Application):
    # disable logging for the profile setup
    error_module = "telegram.ext.AIORateLimiter"
    prev_level = logging.getLogger(error_module).level

    try:  # profile setup has a very long cool-down
        logging.getLogger(error_module).setLevel(logging.ERROR)
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        _ = new_loop.run_until_complete(_setup_profile(app))
        logging.getLogger(error_module).setLevel(prev_level)
    except Exception:
        bot.logger.warning("Bot profile could not be set up")


def setup_handlers(app: telegram_extensions.Application):
    app.add_error_handler(_error_handler)
    for button_handler in core.Button.all_handlers():
        app.add_handler(button_handler)
    for command in commands.Command.all_commands():
        app.add_handler(command.handler, command.group)
    for handler in handlers.MessageHandler.all_handlers():
        app.add_handler(handler.handler, handler.group)
    config_menu = config_menus.BotSettingsMenu()
    app.add_handler(config_menu.handler, config_menu.group)


async def _error_handler(update, context: telegram_extensions.CallbackContext):
    import bot.formatter
    import bot.telegram_utils

    # reply with the error message if possible
    if isinstance(update, telegram.Update) and update.effective_message:
        message = core.TelegramMessage(update.effective_message)
        error = bot.formatter.format_message(str(context.error))
        await bot.telegram_utils.reply_code(message, error)
    # re-raise the error to be logged
    raise context.error or Exception("Unknown error encountered...")


async def _setup_profile(app):
    chat_bot: telegram_extensions.ExtBot = app.bot
    cmds = [cmd.bot_command for cmd in commands.Command.all_commands()]
    await chat_bot.set_my_name("ChatGPT_Dev" if bot.dev_mode else "ChatGPT")
    await chat_bot.set_my_description("ChatGPT based Telegram bot.")
    await chat_bot.set_my_short_description("ChatGPT bot.")
    await chat_bot.set_my_commands(cmds)
