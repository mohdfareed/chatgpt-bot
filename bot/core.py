"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to handlers."""

import asyncio
import os
import secrets

import requests
import telegram
import telegram.ext as telegram_extensions

from bot import commands, formatter, handlers, logger, utils

bot_token = os.getenv("TELEGRAM_BOT_TOKEN") or ""
"""Telegram bot token."""
webhook = os.getenv("WEBHOOK") or ""
"""Telegram webhook URL."""
webhook_addr = os.getenv("WEBHOOK_ADDR") or ""
"""Telegram webhook IP address."""
webhook_port = int(os.getenv("WEBHOOK_PORT") or -1)
"""Telegram webhook port."""
dev_mode = not (webhook and webhook_addr and (webhook_port > -1))
"""Whether the bot is running in development mode (polling mode)."""


def run():
    """Setup and run the bot."""

    # setup bot settings
    defaults = telegram_extensions.Defaults(
        parse_mode=telegram.constants.ParseMode.HTML,
        allow_sending_without_reply=True,
        quote=True,
        block=False,
    )

    # setup the bot application
    application = (
        telegram_extensions.Application.builder()
        .token(bot_token)
        .rate_limiter(
            telegram_extensions.AIORateLimiter()
        )  # TODO: implement custom rate limiter
        .defaults(defaults)
        .build()
    )

    # setup the bot's handlers
    application.add_error_handler(_error_handler)
    # asyncio.run(_setup_profile(application))
    # asyncio.run(_setup_commands(application))
    _setup_commands(application)
    _setup_handlers(application)

    # start the bot
    logger.info("[green]Starting telegram bot...[/green]")
    if not dev_mode:  # run in webhook mode for production
        logger.info(
            f"Using webhook: {webhook} [{webhook_addr}:{webhook_port}]"
        )
        application.run_webhook(
            listen=webhook_addr,
            port=webhook_port,
            webhook_url=webhook,
            secret_token=secrets.token_hex(32),
        )
    else:  # run in polling mode for development
        logger.warning("Running in development mode")
        application.run_polling()
    logger.info("Telegram bot has stopped")


async def _setup_profile(app: telegram_extensions.Application):
    bot: telegram_extensions.ExtBot = app.bot
    await bot.set_my_name("ChatGPT_Dev")
    await bot.set_my_description("ChatGPT based Telegram bot.")
    await bot.set_my_short_description("ChatGPT bot.")


def _setup_commands(app: telegram_extensions.Application):
    bot_commands = []
    for command in commands.all_commands():
        app.add_handler(command.handler, command.group)
        bot_commands.append(command.bot_command)
    bot: telegram_extensions.ExtBot = app.bot
    # await bot.set_my_commands(bot_commands)
    # asyncio.run(bot.set_my_commands(bot_commands))


def _setup_handlers(app: telegram_extensions.Application):
    app.add_handler(
        telegram_extensions.MessageHandler(
            filters=telegram_extensions.filters.ChatType.PRIVATE,
            callback=handlers.private_callback,
        )
    )

    app.add_handler(
        telegram_extensions.MessageHandler(
            filters=telegram_extensions.filters.Entity(
                telegram.constants.MessageEntityType.MENTION
            ),
            callback=handlers.mention_callback,
        )
    )

    app.add_handler(
        telegram_extensions.MessageHandler(
            filters=telegram_extensions.filters.ALL,
            callback=handlers.store_update,
        )
    )


async def _error_handler(update, context: telegram_extensions.CallbackContext):
    logger.exception(context.error)

    if isinstance(update, telegram.Update):
        error = formatter.md_html(str(context.error))
        await utils.reply_code(update.effective_message, error)


# validate token
_url = f"https://api.telegram.org/bot{bot_token}/getMe"
if requests.get(_url).status_code != 200:  # invalid token
    raise ValueError(f"Invalid Telegram bot token: {bot_token}")
