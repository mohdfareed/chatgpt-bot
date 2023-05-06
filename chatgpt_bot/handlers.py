"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

from email import message
from math import e

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from chatgpt_bot import core, logger
from database import utils as db


async def store_update(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (message := update.effective_message):
        return
    core.store_message(message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    logger.debug("mention_callback")
    if not (message := update.effective_message):
        return
    core.store_message(message)

    if not message.text:
        return
    if context.bot.username not in message.text:
        return

    await core.reply_to_message(message, context.bot)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    logger.debug("private_callback")
    if not (message := update.effective_message):
        return
    if not message.text:
        return

    core.store_message(message)
    await core.reply_to_message(message, context.bot)


async def delete_history(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Delete a chat."""

    if not update.effective_chat:
        return

    logger.info(f"deleting chat: {update.effective_chat.id}")
    chat_id, topic_id = update.effective_chat.id, None
    if update.effective_message and update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    db.delete_messages(chat_id, topic_id)
    raise ApplicationHandlerStop  # don't handle elsewhere


async def send_usage(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Send usage instructions."""

    if not update.effective_message:
        return

    if (update.effective_message.is_topic_message and
            update.effective_message.message_thread_id):
        chat_usage = db.get_topic(
            update.effective_message.message_thread_id,
            update.effective_chat.id
        ).usage
        thread_id = update.effective_message.message_thread_id
    else:
        chat_usage = db.get_chat(update.effective_chat.id).usage
        thread_id = None

    user_usage = db.get_user(update.effective_user.id).usage
    await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        text=(f"User usage: {user_usage}\n" +
              f"Chat usage: {chat_usage}"),
        message_thread_id=thread_id,
        reply_to_message_id=update.effective_message.message_id
    )


async def bot_updated(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # update.my_chat_member  # bot member status changed
    pass
