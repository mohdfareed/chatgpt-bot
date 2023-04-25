"""The ChatGPT Telegram bot."""

from telegram import MessageEntity, Update
from telegram.constants import MessageEntityType
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from chatgpt_bot import BOT_TOKEN, logger
from chatgpt_bot.core import (dummy_callback, mention_callback,
                              private_callback, store_message)


def run():
    """Run the bot."""

    # setup the bot
    logger.info("starting telegram bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # add handlers
    app.add_error_handler(error_handler)
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE,
                                   callback=private_callback))
    app.add_handler(MessageHandler(filters.Entity(MessageEntityType.MENTION),
                                   callback=mention_callback))
    app.add_handler(MessageHandler(filters.ALL,
                                   callback=store_message))
    # start the bot
    app.run_polling()
    logger.info("telegram bot has stopped")


async def error_handler(_, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.error(f"error: {context.error}")
