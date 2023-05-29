"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

import asyncio
import html
import re
import traceback

from chatgpt.types import MessageRole
from telegram import Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

import database
from chatgpt_bot import core, formatter, logger
from database import utils as db

dummy_message = """
<b>bold</b>, <i>italic</i>, <u>underline < ><s>strikethrough</s> </u>, <s>strikethrough</s>
<tg-spoiler>spo&iler</tg-spoiler>, <code>inline fixed-width code</code>
<a href="http://www.example.com/">inline <&> >> URL</a>, @{bot}

&
&&&
<
>>>

<b>bold <i>italic bold <s>italic bold strikethrough <tg-spoiler>italic bold strikethrough spoiler</tg-spoiler></s> <u>underline italic bold</u></i> bold</b>

<bad tag>some & text</bad tag>
<b>bold & test <>>>><< &<test>&</b>
<test><tst>te&st</tst></test>

&lt;test&gt;some & text&lt;/test&gt;
<test>;some & text</test>;

<tst>te&st</tst>
<a test="http://www.example.com/">inline <&> >> URL</a>
"""


_sessions_prompts = dict()


async def error_handler(_, context: ContextTypes.DEFAULT_TYPE):
    logger.error(context.error)
    traceback_str = "".join(traceback.format_tb(context.error.__traceback__))
    logger.error("traceback:\n%s", traceback_str)


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dummy_message
    # dummy_message = dummy_message.format(bot=context.bot.username)
    # dummy_message = core._format_text(dummy_message)
    dummy_message = formatter._parse_html(dummy_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dummy_message.format(bot=context.bot.username),
        parse_mode=ParseMode.HTML,
    )


async def store_update(update: Update, _: ContextTypes.DEFAULT_TYPE):
    from chatgpt.langchain import agent, memory

    if not (message := update.effective_message):
        return
    core.store_message(message)
    if not message.text:
        return

    chat_id, topic_id = update.effective_chat.id, None
    if update.effective_message and update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    # setup message metadata
    metadata = dict(
        id=str(message.message_id),
        username=message.from_user.username or message.from_user.first_name
        if message.from_user.username
        else None,
        reply_to=str(message.reply_to_message.message_id)
        if message.reply_to_message
        else None,
    )
    text = agent.parse_message(message.text, metadata, "other")
    session = f"{chat_id}-{topic_id or 0}"
    memory.ChatMemory.store(text, database.URL, session)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    await check_file(update, context)
    return

    await store_update(update, context)

    if not (message := update.effective_message):
        return
    if not message.text:
        return

    await core.reply_to_message(message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    # await store_update(update, context)

    if not update.effective_message.text:
        return
    if context.bot.username not in update.effective_message.text:
        return

    await check_file(update, context)
    return

    await private_callback(update, context)


async def delete_history(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Delete a chat."""

    if not update.effective_chat:
        return

    chat_id, topic_id = update.effective_chat.id, None
    if update.effective_message and update.effective_message.is_topic_message:
        topic_id = update.effective_message.message_thread_id

    from chatgpt.langchain import agent, memory, tools

    session = f"{chat_id}-{topic_id or 0}"
    memory.ChatMemory.delete(database.URL, session)

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
            message.message_thread_id, message.chat_id
        ).usage
        thread_id = message.message_thread_id
    else:
        chat_usage = db.get_chat(update.effective_chat.id).usage

    user_usage = db.get_user(update.effective_user.id).usage
    await update.effective_message.reply_html(
        text=(
            f"<code>User usage: {user_usage}\n"
            + f"Chat usage: {chat_usage}</code>"
        )
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
        _msg = update.effective_message.text.split(" ", 1)[1]
        if _msg.startswith("$"):
            name = _msg.split("$", 1)[1].split("\n", 1)[0]
            text = _msg.split("\n", 1)[1]
        else:
            name = None
            text = _msg
    except IndexError:
        pass

    # parse text from reply
    if not text:
        if update.effective_message.is_topic_message:
            if (
                update.effective_message.message_thread_id
                != update.effective_message.reply_to_message.message_id
            ):
                text = update.effective_message.reply_to_message.text
        elif update.effective_message.reply_to_message:
            text = update.effective_message.reply_to_message.text

    # check validity of the name and text
    if name and len(re.findall(r"^[^a-zA-Z0-9_-]{1,64}$", name)) > 0:
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
    _sessions_prompts[f"{chat_id}-{topic_id or 0}"] = text
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

    session = f"{chat_id}-{topic_id or 0}"
    text = _get_session_prompt(session) or "No system message found."
    await _.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=topic_id,  # type: ignore
        text=f"<code>{text}</code>",
        parse_mode=ParseMode.HTML,
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

    from chatgpt.langchain import agent, memory, tools

    import database
    from chatgpt_bot.formatter import markdown_to_html

    update.message.reply_to_message

    # set typing status
    bot_message = await message.reply_text("<code>Thinking...</code>")
    topic_id: int = 0
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id
    await message.chat.send_action(ChatAction.TYPING, topic_id or None)  # type: ignore
    reply_text = ""
    chunk_counter = 0

    async def send_packet(packet: str, flush: bool = False):
        nonlocal reply_text, chunk_counter

        # send packet to chat
        reply_text = packet if flush else reply_text + packet
        chunk_counter = (chunk_counter + 1) % 10
        if chunk_counter != 0 and not flush:
            return
        message_text = markdown_to_html(reply_text)
        if message_text != bot_message.text_html:
            await bot_message.edit_text(message_text)

    # set up agent components
    session = f"{message.chat_id}-{topic_id or 0}"
    agent_memory = memory.ChatMemory(
        token_limit=2600, url=database.URL, session_id=session
    )
    # agent_tools = [
    #     tools.InternetSearch(),
    #     tools.WikiSearch(),
    #     tools.Calculator(),
    # ]
    chat_agent = agent.ChatGPT(
        # tools=agent_tools,
        token_handler=send_packet,
        memory=agent_memory,
        system_prompt=_get_session_prompt(session),
    )

    # setup message metadata
    metadata = dict(
        id=str(message.message_id),
        username=message.from_user.username or message.from_user.first_name
        if message.from_user.username
        else None,
        reply_to=str(message.reply_to_message.message_id)
        if message.reply_to_message
        else None,
    )
    # clear None values
    metadata = {k: v for k, v in metadata.items() if v is not None}

    # set bot message metadata
    reply_metadata = dict(
        id=str(bot_message.message_id),
        username=bot_message.from_user.username,
        reply_to=str(bot_message.reply_to_message.message_id)
        if bot_message.reply_to_message
        else None,
    )
    # clear None values
    reply_metadata = {k: v for k, v in reply_metadata.items() if v is not None}

    # generate response
    content = message.text or message.caption or ""
    response = await chat_agent.generate(content, metadata, reply_metadata)
    # await bot_message.edit_text(markdown_to_html(response.text))


async def set_chad(update: Update, _: ContextTypes.DEFAULT_TYPE):
    from chatgpt.langchain import prompts

    if not (message := update.effective_message):
        return

    topic_id: int = 0
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id

    session = f"{message.chat_id}-{topic_id or 0}"
    _sessions_prompts[session] = prompts.CHADGPT_PROMPT


def _get_session_prompt(session: str):
    from chatgpt.langchain import prompts

    return _sessions_prompts.get(session, prompts.ASSISTANT_PROMPT)
