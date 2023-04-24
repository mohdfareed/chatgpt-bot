"""The ChatGPT Telegram bot."""

from telegram import Update
from telegram.constants import MessageEntityType
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from chatgpt_bot import BOT_TOKEN, logger
from chatgpt_bot.core import dummy_callback, reply_callback, store_callback


def run():
    """Run the bot."""

    # setup the bot
    logger.info("starting telegram bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # add handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler('start', dummy_callback))
    app.add_handler(MessageHandler(filters.REPLY, callback=reply_callback))
    # app.add_handler(MessageHandler(filters.ALL, callback=dummy_callback))
    # every message handler
    app.add_handler(MessageHandler(filters.ALL, callback=store_callback))
    # app.add_handler(MessageHandler(filters.ChatType.PRIVATE,
    #                                callback=reply_callback))

    # start the bot
    app.run_polling()
    logger.info("telegram bot has stopped")


async def error_handler(_, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.error(f"error: {context.error}")
