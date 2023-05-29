"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

from chatgpt.langchain import agent, memory, prompts
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

import database as _database
from chatgpt_bot import formatter, logger, models, utils
from chatgpt_bot.formatter import markdown_to_html
from database import models as _db_models

dummy_message = """
<b>bold</b>, <i>italic</i>, <u>underline</u>, <s>strikethrough</s>, \
<tg-spoiler>spoiler</tg-spoiler>, <code>inline fixed-width code</code>
<a href="http://www.example.com/">Inline URL</a>
@{bot}
"""


_sessions_prompts = dict()


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.exception(context.error)

    if isinstance(update, Update):
        await utils.reply_code(update.effective_message, context.error)


async def dummy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dummy_message

    dummy_message = formatter._parse_html(dummy_message)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=dummy_message.format(bot=context.bot.username),
        parse_mode=ParseMode.HTML,
    )


async def store_update(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.message or update.channel_post):
        return  # TODO: update edited messages (user effective message)
    message = models.TextMessage(update_message)

    text = agent.parse_message(message.text, message.metadata, "other")
    memory.ChatMemory.store(text, _database.url, message.session)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""
    await check_file(update, context)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)

    if context.bot.username not in message.text:
        return

    await check_file(update, context)


async def delete_history(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Delete a chat."""

    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)

    memory.ChatMemory.delete(_database.url, message.session)
    await utils.reply_code(update_message, "Chat history deleted")
    # raise ApplicationHandlerStop  # don't handle elsewhere


async def send_usage(update: Update, _: ContextTypes.DEFAULT_TYPE):
    """Send usage instructions."""

    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)
    db_user = _db_models.User.get(message.user.id)
    db_chat = _db_models.Chat.get(message.chat.id)

    await utils.reply_code(
        update_message,
        f"User usage: {db_user.usage}\nChat usage: {db_chat.usage}",
    )


async def bot_updated(update: Update, _: ContextTypes.DEFAULT_TYPE):
    # update.my_chat_member  # bot member status changed
    pass


async def edit_sys(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)

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
    _sessions_prompts[message.session] = sys_message
    await utils.reply_code(
        update_message,
        f"<b>New system message:</b>\n{sys_message}",
    )


async def get_sys(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)

    text = (
        utils.get_prompt(message.session, _sessions_prompts)
        or "No system message found."
    )
    await utils.reply_code(update_message, text)


async def check_file(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)

    # set typing status
    bot_message = await update_message.reply_text("<code>Thinking...</code>")
    reply = models.TextMessage(bot_message)
    await update_message.chat.send_action(ChatAction.TYPING, message.topic_id)  # type: ignore

    # setup streaming variables
    reply_text = ""
    chunk = ""
    chunk_counter = 0
    chunk_size = 10
    results: agent.GenerationResults | None = None  # type: ignore

    async def send_packet(packet: str | agent.GenerationResults):
        nonlocal reply_text, chunk_counter, chunk, results
        flushing = isinstance(packet, agent.GenerationResults)

        if flushing:  # flush chunk
            chunk_counter = -1
            results = packet

        # add packet to reply
        chunk += packet if not flushing else ""
        chunk_counter = (chunk_counter + 1) % chunk_size
        if chunk_counter != 0:
            return

        # send packet to chat
        new_reply = reply_text + chunk
        if reply_text != new_reply:
            await bot_message.edit_text(markdown_to_html(new_reply))
            reply_text = new_reply
            chunk = ""

    # agent_tools = [
    #     tools.InternetSearch(),
    #     tools.WikiSearch(),
    #     tools.Calculator(),
    # ]
    # set up agent components
    agent_memory = memory.ChatMemory(
        token_limit=2600, url=_database.url, session_id=message.session
    )
    chat_agent = agent.ChatGPT(
        # tools=agent_tools,
        token_handler=send_packet,
        memory=agent_memory,
        system_prompt=utils.get_prompt(message.session, _sessions_prompts),
    )
    # generate response
    await chat_agent.generate(message.text, message.metadata, reply.metadata)

    # count usage if message was sent
    if isinstance(results, agent.GenerationResults):
        usage = results.prompt_tokens + results.generated_tokens

        db_user = _db_models.User.get(message.user.id)
        db_user.usage += usage
        db_user.store()

        db_chat = _db_models.Chat.get(message.chat.id)
        db_chat.usage += usage
        db_chat.store()


async def set_chad(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)
    _sessions_prompts[message.session] = prompts.CHADGPT_PROMPT
    await utils.reply_code(update_message, "Mode activated")
