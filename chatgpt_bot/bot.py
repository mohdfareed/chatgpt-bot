"""The ChatGPT Telegram bot. This module contains the bot's entry point. It
manages the bot's lifecycle and tunneling updates to the handlers."""

from telegram.constants import MessageEntityType
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from chatgpt_bot import BOT_TOKEN, logger
from chatgpt_bot.handlers import (dummy_callback, mention_callback,
                                  private_callback, store_update)


def run():
    """Run the bot."""

    # setup the bot
    logger.info("starting telegram bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # add handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler('dummy', dummy_callback))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE,
                                   callback=private_callback))
    app.add_handler(MessageHandler(filters.Entity(MessageEntityType.MENTION),
                                   callback=mention_callback))
    app.add_handler(MessageHandler(filters.ALL,
                                   callback=store_update))
    # start the bot
    app.run_polling()
    logger.info("telegram bot has stopped")


async def error_handler(_, context: ContextTypes.DEFAULT_TYPE):
    """Log Errors caused by Updates."""
    logger.debug(context.error.__traceback__.__str__())
    logger.error(f"error: {context.error}")
