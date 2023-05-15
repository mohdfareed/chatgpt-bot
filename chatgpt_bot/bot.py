"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to the handlers."""

import secrets

from telegram.constants import MessageEntityType
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from chatgpt_bot import BOT_TOKEN, DEV, WEBHOOK, WEBHOOK_ADDR, WEBHOOK_PORT
from chatgpt_bot.handlers import *


def run():
    """Run the bot."""

    # setup the bot
    logger.info("starting telegram bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    _setup(app)

    # start the bot
    if not DEV:
        app.run_webhook(
            listen=WEBHOOK_ADDR, port=WEBHOOK_PORT,
            webhook_url=WEBHOOK, secret_token=secrets.token_hex(32)
        )
    else:  # run in polling mode for development
        logger.warning("running in development mode")
        app.run_polling()
    logger.info("telegram bot has stopped")


def _setup(app: Application):
    """Setup the bot's update handlers."""
    # add error/command handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler('delete', delete_history, block=False))
    app.add_handler(CommandHandler('usage', send_usage, block=False))
    app.add_handler(CommandHandler('start', dummy_callback, block=False))
    app.add_handler(CommandHandler('sys', get_sys, block=False))
    app.add_handler(CommandHandler('edit', edit_sys, block=False))
    app.add_handler(CommandHandler('cancel', cancel_reply, block=False))

    # add message handlers
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE, block=False,
        callback=private_callback
    ))
    app.add_handler(MessageHandler(
        filters.Entity(MessageEntityType.MENTION), block=False,
        callback=mention_callback
    ))
    app.add_handler(MessageHandler(
        filters.ALL, block=False,
        callback=store_update
    ))
    app.add_handler(MessageHandler(
        filters.ATTACHMENT, block=False,
        callback=check_file
    ))
