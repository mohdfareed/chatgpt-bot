"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""


from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from chatgpt_bot import core, logger
from database import utils as db

dummy_string = """
*bold \\*text*
_italic \\*text_
__underline__
~strikethrough~
||spoiler||
*bold _italic bold ~italic bold strikethrough ||italic bold strikethrough spoiler||~ __underline italic bold___ bold*
[inline URL](http://www.example.com/)
[inline mention of a user](tg://user?id=123456789)
![👍](tg://emoji?id=5368324170671202286)
`inline fixed-width code`
```
pre-formatted fixed-width code block
```
```python
pre-formatted fixed-width code block written in the Python programming language
```
"""


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = {
        'chat_id': update.effective_chat.id,
        'message_thread_id': update.message.message_thread_id,
        'parse_mode': 'MarkdownV2',
        'text': dummy_string,
    }
    await context.bot.send_message(**message)


async def store_update(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (message := update.effective_message):
        return
    core.store_message(message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    logger.info("mention_callback")
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

    logger.info("private_callback")
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


async def bot_updated(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # update.my_chat_member  # bot member status changed
    pass
