"""The bot's core functionality."""

from chatgpt.chat import Chat
from chatgpt.chat_completion import ChatCompletion
from chatgpt.message import Prompt, Reply
from telegram import Update
from telegram.ext import ContextTypes

chatgpt = ChatCompletion()


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(update.effective_chat.id,  # type: ignore
                                   text="ChatGPT bot has started.")


async def reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message is None:
        return
    if update.message.reply_to_message.from_user.id != context.bot.id:
        return
    if update.message.text is None:
        return

    message = Prompt('user', update.message.text)
    chat_context = Chat(messages=[message]).to_messages()
    response = chatgpt.request(chat_context)

    await context.bot.send_message(update.effective_chat.id,  # type: ignore
                                   text=response.content)
