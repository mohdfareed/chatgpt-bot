"""Command handlers for telegram command updates. It is responsible for parsing
updates and executing core module functionality."""

from telegram import Update
from telegram.ext import ContextTypes

import bot.models
import database
from bot import formatter, utils
from chatgpt.langchain import memory

usage_message = """
Set the system prompt by including the prompt in the message. For example:
`/edit_sys@{bot} The new system prompt.`
You can also reply to a message with `/edit_sys@{bot}` to use the text of that
message as the system prompt.
"""


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    global usage_message

    if not update.effective_message:
        return

    dummy_message = formatter.md_html._parse_html(usage_message)
    dummy_message = dummy_message.format(bot=context.bot.username)
    await update.effective_message.reply_html(dummy_message)


async def edit_sys(update: Update, _):
    """Edit the system message."""

    if not (update_message := update.effective_message):
        return
    message = bot.models.TextMessage(update_message)

    sys_message = None
    try:  # parse the message in the format `/command content`
        sys_message = message.text.split(" ", 1)[1].strip()
    except IndexError:
        pass

    # parse text from reply if no text was found in message
    if not sys_message and message.reply:
        sys_message = message.reply.text
    if not sys_message:
        raise ValueError("No text found in message or reply")

    # create new system message
    utils.save_prompt(message.chat.id, message.topic_id, sys_message)
    await utils.reply_code(
        update_message,
        f"<b>New system message:</b>\n{sys_message}",
    )


async def get_sys(update: Update, _):
    """Send the system message."""

    if not (update_message := update.effective_message):
        return
    message = bot.models.TextMessage(update_message)

    text = (
        utils.load_prompt(message.chat.id, message.topic_id)
        or "No system message found."
    )
    await utils.reply_code(update_message, text)


async def delete_history(update: Update, _):
    """Delete a chat's history."""

    if not (update_message := update.effective_message):
        return
    message = bot.models.TextMessage(update_message)

    memory.ChatMemory.delete(database.url, message.session)
    await utils.reply_code(update_message, "Chat history deleted")
    # raise ApplicationHandlerStop  # don't handle elsewhere


async def send_usage(update: Update, _):
    """Send usage instructions."""

    if not (update_message := update.effective_message):
        return
    message = bot.models.TextMessage(update_message)
    db_user = database.models.User(message.user.id).load()
    db_chat = database.models.Chat(message.chat.id).load()

    await utils.reply_code(
        update_message,
        f"User usage: {db_user.usage}\nChat usage: {db_chat.usage}",
    )
