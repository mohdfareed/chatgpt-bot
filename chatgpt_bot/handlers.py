"""Handlers for telegram updates. It is responsible for parsing updates and
executing core module functionality."""

from chatgpt.langchain import agent, memory, prompts
from telegram import Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationHandlerStop, ContextTypes

import database as _database
from chatgpt_bot import formatter, logger, models, utils
from chatgpt_bot.formatter import markdown_to_html
from database import models as _db_models


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


async def check_file(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if not (update_message := update.effective_message):
        return
    message = models.TextMessage(update_message)
    # set typing status
    bot_message = await update_message.reply_text("<code>Thinking...</code>")
    reply = models.TextMessage(bot_message)
    await update_message.chat.send_action(ChatAction.TYPING, message.topic_id)  # type: ignore

    # agent_tools = [
    #     tools.InternetSearch(),
    #     tools.WikiSearch(),
    #     tools.Calculator(),
    # ]
    # set up agent components
    agent_memory = memory.ChatMemory(
        token_limit=2600, url=_database.url, session_id=message.session
    )
    token_handler = StreamHandler(update_message)
    token_handler.reply = bot_message
    chat_agent = agent.ChatGPT(
        # tools=agent_tools,
        token_handler=token_handler.handle_packet,
        memory=agent_memory,
        system_prompt=utils.get_sys_prompt(message.session),
    )
    # generate response
    results = await chat_agent.generate(
        message.text, message.metadata, reply.metadata
    )
    # count usage if message was sent
    count_usage(message, results)


def count_usage(message: models.TextMessage, results: agent.GenerationResults):
    # count usage if message was sent
    usage = results.prompt_tokens + results.generated_tokens

    db_user = _db_models.User.get(message.user.id)
    db_user.token_usage += usage
    db_user.usage += results.cost
    db_user.store()

    db_chat = _db_models.Chat.get(message.chat.id, message.topic_id)
    db_chat.token_usage += usage
    db_chat.usage += results.cost
    db_chat.store()


class StreamHandler:
    """Handles streaming of a message by sending the stream in chunks."""

    CHUNK_SIZE = 10
    """Number of packets to send before flushing."""
    reply: Message | None = None
    """The reply message to which tokens are streamed."""

    def __init__(self, message: Message):
        """Initialize the stream handler and return its handling method.

        Args:
            message (Message): The message to which the stream is replying.
        """
        self._message = message
        self._last_message = ""
        self._chunk = ""
        self._chunk_counter = 0

    async def handle_packet(self, packet: str | None):
        """Send a packet to the chat. Stream is flushed on a 'None' packet."""

        # append packet to chunk
        self._chunk += packet or ""
        self._chunk_counter = (self._chunk_counter + 1) % self.CHUNK_SIZE
        if packet and self._chunk_counter != 0:
            return

        # send packet to chat
        new_message = self._last_message + self._chunk
        new_message = markdown_to_html(new_message)
        if self._last_message != new_message:
            await self._send_message(new_message)
            self._last_message = new_message
            self._chunk = ""

    async def _send_message(self, text: str):
        # send new message if no reply has been sent yet
        if not self.reply:
            self.reply = await self._message.reply_html(text)
            return
        # edit the existing reply otherwise
        await self.reply.edit_text(text)
