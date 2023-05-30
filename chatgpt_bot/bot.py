"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to handlers."""

import secrets as _secrets

import telegram as _telegram
import telegram.ext as _telegram_extensions
from telegram import constants as _telegram_constants

import chatgpt_bot as _bot
import chatgpt_bot.commands as _commands
import chatgpt_bot.handlers as _handlers
import chatgpt_bot.utils as _utils


def run():
    """Setup and run the bot."""

    # setup bot settings
    defaults = _telegram_extensions.Defaults(
        parse_mode=_telegram_constants.ParseMode.HTML,
        allow_sending_without_reply=True,
        quote=True,
        block=False,
    )

    # setup the bot application
    application = (
        _telegram_extensions.Application.builder()
        .token(_bot.token)
        .rate_limiter(
            _telegram_extensions.AIORateLimiter()
        )  # TODO: implement custom rate limiter
        .defaults(defaults)
        .build()
    )

    # setup the bot's handlers
    application.add_error_handler(_error_handler)
    _setup_commands(application)
    _setup_handlers(application)

    # start the bot
    _bot.logger.info("Starting telegram bot...")
    if not _bot.dev_mode:  # run in webhook mode for production
        _bot.logger.info(
            f"Using webhook: {_bot.webhook} "
            f"[{_bot.webhook_addr}:{_bot.webhook_port}]"
        )
        application.run_webhook(
            listen=_bot.webhook_addr,
            port=_bot.webhook_port,
            webhook_url=_bot.webhook,
            secret_token=_secrets.token_hex(32),
        )
    else:  # run in polling mode for development
        _bot.logger.warning("Running in development mode")
        application.run_polling()
    _bot.logger.info("Telegram bot has stopped")


def _setup_commands(app: _telegram_extensions.Application):
    # setup command handlers

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="delete",
            callback=_commands.delete_history,
        )
    )

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="usage",
            callback=_commands.send_usage,
        )
    )

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="start",
            callback=_commands.dummy_callback,
        )
    )

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="sys",
            callback=_commands.get_sys,
        )
    )

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="edit",
            callback=_commands.edit_sys,
        )
    )

    app.add_handler(
        _telegram_extensions.CommandHandler(
            command="chad",
            callback=_commands.set_chad,
        )
    )


def _setup_handlers(app: _telegram_extensions.Application):
    # setup message handlers

    app.add_handler(
        _telegram_extensions.MessageHandler(
            filters=_telegram_extensions.filters.ChatType.PRIVATE,
            callback=_handlers.private_callback,
        )
    )

    app.add_handler(
        _telegram_extensions.MessageHandler(
            filters=_telegram_extensions.filters.Entity(
                _telegram_constants.MessageEntityType.MENTION
            ),
            callback=_handlers.mention_callback,
        )
    )

    app.add_handler(
        _telegram_extensions.MessageHandler(
            filters=_telegram_extensions.filters.ALL,
            callback=_handlers.store_update,
        )
    )


async def _error_handler(
    update, context: _telegram_extensions.CallbackContext
):
    _bot.logger.exception(context.error)

    if isinstance(update, _telegram.Update):
        await _utils.reply_code(update.effective_message, context.error)
