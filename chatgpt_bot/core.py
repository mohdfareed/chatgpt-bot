"""The bot's core functionality."""

from bdb import effective

from chatgpt.chat import Chat
from chatgpt.chat_completion import ChatCompletion
from chatgpt.message import Message as GPTMessage
from chatgpt.message import Prompt
from telegram import Message, MessageEntity, Update
from telegram.ext import ContextTypes, ExtBot

from chatgpt_bot import logger
from chatgpt_bot.utils import stream_message
from database import models
from database import utils as db


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = {
        'chat_id': update.effective_chat.id,
        'message_thread_id': update.message.message_thread_id,
        'text': "This is a dummy message.",
    }
    await context.bot.send_message(**message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    logger.info("mention_callback")
    await store_message(update, context)
    message = update.effective_message
    if not message or not message.text:
        return
    if context.bot.username not in message.text:
        return
    await send_message(message, context.bot)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    logger.info("private_callback")
    await store_message(update, context)
    message = update.effective_message
    if not message:
        return
    await send_message(message, context.bot)


async def send_message(message: Message, bot: ExtBot):
    """Reply to a message."""

    sys_prompt = """
    You are a friendly member of a chat group. You will talk as yourself. Be
    genuine and transparent. You will not be judged for your opinions. You
    will act as a person who is talking with their friends.
    """

    if not message.text:
        return

    chat_messages: list[GPTMessage] = [
        Prompt('system', sys_prompt),
        Prompt('user', message.text.replace(f"@{bot.username}", '')),
    ]
    chat_context = Chat(messages=chat_messages).to_messages()
    chatgpt = ChatCompletion()
    try:
        await stream_message(chatgpt, bot, chat_context, message.chat.id,
                             message.message_thread_id)
    except Exception as e:
        chatgpt.cancel()  # cancel the request if it hasn't already finished
        raise RuntimeError(f"error streaming message: {e}")


async def store_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Store the message in the database."""
    if ((not update.effective_user) or
        (not update.effective_user.username) or
        (not update.effective_message) or
            (not update.effective_message.text)):
        return

    user = models.User(id=update.effective_user.id,
                       username=update.effective_user.username)
    message = models.Message(id=update.effective_message.message_id,
                             chat_id=update.effective_message.chat_id,
                             topic_id=update.effective_message.message_thread_id,
                             user_id=update.effective_user.id,
                             text=update.effective_message.text)

    db.add_user(user)
    db.add_message(message)
