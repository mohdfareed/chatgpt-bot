"""The ChatGPT Telegram bot."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TOKEN


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id,  # type: ignore
                                   text="I'm a bot, please talk to me!")


def run():
    """Run the bot."""

    # setup the bot
    print("starting telegram bot...")
    app = Application.builder()
    app = app.token(TOKEN).build()

    # add handlers
    app.add_handler(CommandHandler('start', start_callback))

    # start the bot
    app.run_polling()


if __name__ == '__main__':
    run()
