"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import html
import re
import traceback

from chatgpt.types import MessageRole
from telegram import Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

from chatgpt_bot import core, logger
from database import utils as db

dummy_message = """
<b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>
<tg-spoiler>spoiler</tg-spoiler>, <code>inline fixed-width code</code>
<a href="http://www.example.com/">inline URL</a>, @{bot}
"""


async def error_handler(_, context: ContextTypes.DEFAULT_TYPE):
    logger.error(context.error)
    traceback_str = ''.join(traceback.format_tb(context.error.__traceback__))
    logger.error("traceback:\n%s", traceback_str)


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dummy_message
    dummy_message = dummy_message.format(bot=context.bot.username)
    dummy_message = core._format_text(dummy_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dummy_message,
        parse_mode=ParseMode.HTML
    )


async def store_update(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await check_file(update, _)
    return
    if not (message := update.effective_message):
        return
    core.store_message(message)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    await store_update(update, context)
    return

    if not (message := update.effective_message):
        return
    if not message.text:
        return

    await core.reply_to_message(message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    await store_update(update, context)

    if not update.effective_message.text:
        return
    if context.bot.username not in update.effective_message.text:
        return

    await private_callback(update, context)


async def delete_history(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Delete a chat."""

    if not update.effective_chat:
        return

    chat_id, topic_id = update.effective_chat.id, None
    if update.effective_message and update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    db.delete_messages(chat_id, topic_id)
    await update.effective_message.reply_html(
        text="<code>Chat history deleted.</code>"
    )
    raise ApplicationHandlerStop  # don't handle elsewhere


async def send_usage(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Send usage instructions."""

    if not (message := update.effective_message):
        return

    thread_id: int = None  # type: ignore
    if message.is_topic_message and message.message_thread_id:
        chat_usage = db.get_topic(
            message.message_thread_id,
            message.chat_id
        ).usage
        thread_id = message.message_thread_id
    else:
        chat_usage = db.get_chat(update.effective_chat.id).usage

    user_usage = db.get_user(update.effective_user.id).usage
    await update.effective_message.reply_html(
        text=(f"<code>User usage: {user_usage}\n" +
              f"Chat usage: {chat_usage}</code>")
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
    sys_message.role = MessageRole.SYSTEM
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

    await _.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=topic_id,  # type: ignore
        text=(text or "No system message found."),
        parse_mode=ParseMode.HTML
    )


async def cancel_reply(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not (msg := update.effective_message):
        return

    if msg.reply_to_message:
        cancelled = await core.cancel_reply(msg.reply_to_message)
    else:
        cancelled = await core.cancel_all(msg)
    # react to message
    if cancelled:
        await msg.reply_html(text="<code>Cancelled.</code>")


async def check_file(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (message := update.effective_message):
        return
    if not update.effective_message.text:
        return

    from chatgpt.langchain import agents, memory, prompts

    import database
    update.message.reply_to_message

    # set typing status
    bot_message = await message.reply_text('<code>Thinking...</code>')
    topic_id: int = None  # type: ignore
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id
    await message.chat.send_action(ChatAction.TYPING, topic_id)

    # set up agent
    agent_memory = memory.ChatMemory(
        token_limit=3200, url=database.URL,
        session_id=str(message.chat_id)
    )
    agent = agents.ChatGPT(
        memory=agent_memory,
        instructions=prompts.TELEGRAM_INSTRUCTIONS,
        system_prompt=prompts.CHADGPT_PROMPT,
    )

    # generate response
    prompt = construct_prompt(message)
    prompt += construct_prompt(bot_message)
    response = await agent.generate(prompt)
    await bot_message.edit_text(core._format_text(response))
    # raise


def construct_prompt(message: Message) -> str:
    """Construct a prompt for the given message."""
    from io import StringIO

    prompt = StringIO()
    prompt.write(f"\n\nusername: {message.from_user.username}")
    prompt.write(f"\nid: {message.message_id}\n")
    if message.reply_to_message:
        prompt.write(f"\nreply_to_id: {message.reply_to_message.id}\n")
    if not message.from_user.is_bot:
        prompt.write(f"Message: {message.text}")

    return prompt.getvalue()
