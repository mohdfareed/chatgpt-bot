"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import html
import re
from email import message

from chatgpt.messages import Message as GPTMessage
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

from chatgpt_bot import core, logger
from database import utils as db

dummy_message = """
<b>bold</b>, <strong>bold</strong>
<i>italic</i>, <em>italic</em>
<u>underline</u>, <ins>underline</ins>


<s>strikethrough</s>, <strike>strikethrough</strike>, <del>strikethrough</del>
<span class="tg-spoiler">spoiler</span>, <tg-spoiler>spoiler</tg-spoiler>
<b>bold <i>italic bold <s>italic bold strikethrough <span class="tg-spoiler">italic bold strikethrough spoiler</span></s> <u>underline italic bold</u></i> bold</b>
<a href="http://www.example.com/">inline URL</a>
<a href="tg://user?id=123456789">inline mention of a user</a>
<tg-emoji emoji-id="5368324170671202286">👍</tg-emoji>
<code>inline fixed-width code</code>
<pre>pre-formatted fixed-width code block</pre>
<pre><code class="language-python">pre-formatted fixed-width code block written in the Python programming language</code></pre>
"""


async def dummy_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    global dummy_message
    dummy_message = core._format_text(dummy_message)
    await _.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dummy_message,
        parse_mode="HTML"
    )


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

    chat_id, topic_id = update.effective_chat.id, None
    if update.effective_message and update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    db.delete_messages(chat_id, topic_id)
    await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=topic_id,
        text="Chat history deleted."
    )
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


async def edit_sys(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_chat and update.effective_message):
        return
    if not update.effective_message.text:
        return

    # get the chat and topic
    chat_id = update.effective_chat.id
    topic_id = None
    if update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id
    # create new system message
    sys_message = db.get_message(-(topic_id or 0), chat_id)

    name, text = None, None
    try:  # parse the message in the format `/command name\ncontent`
        _msg = update.effective_message.text.split(' ', 1)[1]
        if _msg.startswith('$'):
            name = _msg.split('$', 1)[1].split('\n', 1)[0]
            text = _msg.split('\n', 1)[1]
        else:
            name = None
            text = _msg
    except IndexError:
        pass

    # parse text from reply
    if not text:
        if update.effective_message.is_topic_message:
            if (update.effective_message.message_thread_id !=
                    update.effective_message.reply_to_message.message_id):
                text = update.effective_message.reply_to_message.text
        elif update.effective_message.reply_to_message:
            text = update.effective_message.reply_to_message.text

    # check validity of the name and text
    if name and len(re.findall(r'^[^a-zA-Z0-9_-]{1,64}$', name)) > 0:
        raise ValueError("invalid name for system message")
    if not text:
        raise ValueError("no text found to update system message")
    # get the chat and topic
    chat_id = update.effective_chat.id
    topic_id = None
    if update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id
    # create new system message
    sys_message = db.get_message(-(topic_id or 0), chat_id)
    sys_message.topic_id = topic_id
    sys_message.role = GPTMessage.Role.SYSTEM
    sys_message.text = text
    sys_message.name = name
    db.add_message(sys_message)


async def get_sys(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update.effective_chat and update.effective_message):
        return
    if not update.effective_message.text:
        return

    # get the chat and topic
    chat_id = update.effective_chat.id
    topic_id = None
    if update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    # get the system message's name and text
    sys_message = db.get_message(-(topic_id or 0), chat_id)
    # create bot message text
    text = ""
    if sys_message.name:
        text += f"<b>Name</b>: {html.escape(sys_message.name)}\n"
    if sys_message.text:
        text += f"<code>{html.escape(sys_message.text or '')}</code>"

    await update.get_bot().send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=topic_id,
        text=(text or "No system message found."),
        parse_mode=ParseMode.HTML
    )
