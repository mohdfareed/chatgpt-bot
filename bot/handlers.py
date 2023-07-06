"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import telegram
import telegram.constants
import telegram.ext as telegram_extensions

import chatgpt.memory
from bot import chat_handler, models

_default_context = telegram_extensions.ContextTypes.DEFAULT_TYPE


async def store_update(update: telegram.Update, _: _default_context):
    if not (update_message := update.message or update.channel_post):
        return  # TODO: update edited messages (user effective message)
    message = models.TextMessage(update_message)

    history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await history.add_message(message.to_chat_message())


async def private_callback(update: telegram.Update, _: _default_context):
    """Reply to a message."""
    if not (update_message := update.message or update.channel_post):
        return
    message = models.TextMessage(update_message)
    await _reply_to_user(message)


async def mention_callback(update: telegram.Update, context: _default_context):
    """Reply to a message."""
    if not (update_message := update.message or update.channel_post):
        return
    message = models.TextMessage(update_message)
    if context.bot.username not in message.text:
        return
    await _reply_to_user(message)


async def _reply_to_user(message: models.TextMessage):
    await chat_handler.generate_reply(message)
