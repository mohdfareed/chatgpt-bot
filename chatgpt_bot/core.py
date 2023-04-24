"""The bot's core functionality."""

from chatgpt.chat import Chat
from chatgpt.chat_completion import ChatCompletion
from chatgpt.message import Prompt, Reply
from telegram import MessageEntity, Update
from telegram.ext import ContextTypes

from chatgpt_bot import logger
from chatgpt_bot.utils import stream_message
from database import utils as db
from database.models import Message, User


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = {
        'chat_id': update.effective_chat.id,
        'message_thread_id': update.message.message_thread_id,
        'text': "This is a dummy message.",
    }
    await context.bot.send_message(**message)


async def reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        if update.message.reply_to_message is not None:
            if update.message.reply_to_message.from_user.id != context.bot.id:
                return
    if update.message.text is None:
        return

    message = Prompt('user', update.message.text)
    chat_context = Chat(messages=[message]).to_messages()
    chatgpt = ChatCompletion()
    try:
        await stream_message(chatgpt, context.bot, update.effective_chat.id,
                             chat_context)
    except Exception as e:
        chatgpt.cancel()  # cancel the request if it hasn't already finished
        raise RuntimeError(f"error streaming message: {e}")


async def store_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == 'private':
        await reply_callback(update, context)
        return
    if update.message.text is None:
        logger.error('message text is None: ' + str(update.message))
        return
    else:
        if update.message.entities != None:
            if (context.bot.username in update.message.text):
                await reply_callback(update, context)
                return

    user = User(id=update.effective_message.from_user.id,
                username=update.message.from_user.username)
    message = Message(id=update.effective_message.message_id,
                      chat_id=update.effective_message.chat_id,
                      topic_id=update.effective_message.message_thread_id,
                      user_id=user.id, text=update.effective_message.text)
    try:
        db.create_user(user)
        db.store_message(message)
    except Exception as e:
        raise RuntimeError(f"error storing user/message: {e}")
