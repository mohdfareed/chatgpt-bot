"""Command handlers for telegram command updates. It is responsible for parsing
updates and executing core module functionality."""

from chatgpt.langchain import memory as _chatgpt_memory
from chatgpt.langchain import prompts as _prompts
from telegram import Update as _Update
from telegram.constants import ParseMode as _ParseMode
from telegram.ext import ContextTypes as _ContextTypes

import database as _database
from chatgpt_bot import models as _bot_models
from chatgpt_bot import utils as _utils
from chatgpt_bot.formatter import markdown_to_html as _markdown_to_html
from database import models as _db_models

dummy_message = """
<b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>, \
<tg-spoiler>spoiler</tg-spoiler>, <code>inline fixed-width code</code>
<a href="http://www.example.com/">Inline URL</a>
@{bot}
"""


async def dummy_callback(update: _Update, context: _ContextTypes.DEFAULT_TYPE):
    global dummy_message

    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)

    dummy_message = _markdown_to_html._parse_html(dummy_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dummy_message.format(bot=context.bot.username),
        parse_mode=_ParseMode.HTML,
    )


async def edit_sys(update: _Update, _):
    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)

    sys_message = None
    try:  # parse the message in the format `/command content`
        sys_message = update.effective_message.text.split(" ", 1)[1].strip()
    except IndexError:
        pass

    # parse text from reply if no text was found in message
    if not sys_message and message.reply:
        sys_message = message.reply.text
    if not sys_message:
        raise ValueError("No text found to update system message")

    # create new system message
    _utils.set_sys_prompt(message.session, sys_message)
    await _utils.reply_code(
        update_message,
        f"<b>New system message:</b>\n{sys_message}",
    )


async def get_sys(update: _Update, _):
    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)

    text = _utils.get_sys_prompt(message.session) or "No system message found."
    await _utils.reply_code(update_message, text)


async def set_chad(update: _Update, _):
    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)
    _utils.set_sys_prompt(message.session, _prompts.CHADGPT_PROMPT)
    await _utils.reply_code(update_message, "Mode activated")


async def delete_history(update: _Update, _):
    """Delete a chat."""

    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)

    _chatgpt_memory.ChatMemory.delete(_database.url, message.session)
    await _utils.reply_code(update_message, "Chat history deleted")
    # raise ApplicationHandlerStop  # don't handle elsewhere


async def send_usage(update: _Update, _):
    """Send usage instructions."""

    if not (update_message := update.effective_message):
        return
    message = _bot_models.TextMessage(update_message)
    db_user = _db_models.User.get(message.user.id)
    db_chat = _db_models.Chat.get(message.chat.id)

    await _utils.reply_code(
        update_message,
        f"User usage: {db_user.usage}\nChat usage: {db_chat.usage}",
    )
