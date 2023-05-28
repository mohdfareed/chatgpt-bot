"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to the handlers."""

import secrets

from telegram.constants import MessageEntityType, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    Defaults,
    MessageHandler,
    filters,
)

from chatgpt_bot import BOT_TOKEN, DEV, WEBHOOK, WEBHOOK_ADDR, WEBHOOK_PORT
from chatgpt_bot.handlers import *


def run():
    """Run the bot."""

    # setup the bot
    defaults = Defaults(  # setup default settings
        parse_mode=ParseMode.HTML,
        allow_sending_without_reply=True,
        quote=True,
        block=False,
    )
    app = (  # setup the application
        Application.builder().token(BOT_TOKEN).defaults(defaults).build()
    )
    _setup_handlers(app)

    # start the bot
    logger.info("starting telegram bot...")
    if not DEV:
        app.run_webhook(
            listen=WEBHOOK_ADDR,
            port=WEBHOOK_PORT,
            webhook_url=WEBHOOK,
            secret_token=secrets.token_hex(32),
        )
    else:  # run in polling mode for development
        logger.warning("running in development mode")
        app.run_polling()
    logger.info("telegram bot has stopped")


def _setup_handlers(app: Application):
    """Setup the bot's update handlers."""

    # add error/command handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("delete", delete_history, block=True))
    app.add_handler(CommandHandler("usage", send_usage))
    app.add_handler(CommandHandler("start", dummy_callback))
    app.add_handler(CommandHandler("sys", get_sys))
    app.add_handler(CommandHandler("edit", edit_sys))
    app.add_handler(CommandHandler("cancel", cancel_reply))
    app.add_handler(CommandHandler("chad", set_chad))

    # add message handlers
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE, callback=private_callback)
    )
    app.add_handler(
        MessageHandler(
            filters.Entity(MessageEntityType.MENTION),
            callback=mention_callback,
        )
    )
    app.add_handler(MessageHandler(filters.ALL, callback=store_update))
    app.add_handler(MessageHandler(filters.ATTACHMENT, callback=check_file))
