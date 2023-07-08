"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to handlers."""

import asyncio
import secrets
import threading

import telegram
import telegram.ext as telegram_extensions

import bot
from bot import commands, formatter, handlers, utils


def run():
    """Setup and run the bot."""
    # asyncio.run(run_async())
    run_async()


def run_async():
    """Setup and run the bot asynchronously."""

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
        .rate_limiter(
            telegram_extensions.AIORateLimiter()
        )  # TODO: implement custom rate limiter
        .defaults(defaults)
        .build()
    )

    # setup the bot
    _setup_handlers(application)
    commands = _setup_commands(application)
    # await _setup_profile(application, commands)
    # asyncio.run(_setup_profile(application, commands))
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(_setup_profile(application, commands))
    # thread = threading.Thread(target=_setup_profile, args=(application,))
    # thread.start()
    # thread.join()
    # FIXME: resolve threading issues

    # start the bot
    bot.logger.info("[green]Starting telegram bot...[/green]")
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


async def _setup_profile(app, commands: list[telegram.BotCommand]):
    bot: telegram_extensions.ExtBot = app.bot
    await bot.set_my_name("ChatGPT_Dev_Bot")
    await bot.set_my_description("ChatGPT based Telegram bot.")
    await bot.set_my_short_description("ChatGPT bot.")
    await bot.set_my_commands(commands)


def _setup_commands(app: telegram_extensions.Application):
    bot_commands = []
    for command in commands.all_commands():
        app.add_handler(command.handler, command.group)
        bot_commands.append(command.bot_command)
    return bot_commands


def _setup_handlers(app: telegram_extensions.Application):
    app.add_error_handler(_error_handler)

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
    if isinstance(update, telegram.Update):
        error = formatter.md_html(str(context.error))
        await utils.reply_code(update.effective_message, error)

    # re-raise the error to be logged
    if context.error:
        raise context.error
