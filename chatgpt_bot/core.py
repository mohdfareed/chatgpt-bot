"""The bot's core functionality and Telegram callbacks."""

import asyncio
import html
import re
from typing import AsyncGenerator

from bs4 import BeautifulSoup
from chatgpt.completion import ChatCompletion
from chatgpt.errors import CompletionError, ConnectionError, TokenLimitError
from chatgpt.model import ChatGPT
from chatgpt.types import GPTChat, GPTMessage, GPTReply, MessageRole
from markdown import markdown
from telegram import Message
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError

from chatgpt_bot import logger, utils
from database import models
from database import utils as db

_edit_timer = 0.0
"""Timer since the last edit message request."""
_requests: dict[str, AsyncGenerator] = dict()
"""Dictionary of reply generators."""


async def cancel_reply(message: Message) -> bool:
    """Cancel a reply to a message."""

    # cancel reply request
    reply = _requests.get(_get_request_id(message), None)
    if not reply:
        return False
    await reply.aclose()
    del _requests[_get_request_id(message)]
    return True


async def cancel_all(message: Message) -> bool:
    """Cancel all requests in chat or topic of message."""

    # get request id pattern
    pattern = f"{message.chat_id}:"
    if message.is_topic_message:
        pattern += f"{message.message_thread_id}:"
    # cancel all requests with pattern
    has_cancelled = False
    for request_id, reply in _requests.copy().items():
        if request_id.startswith(pattern):
            await reply.aclose()
            del _requests[request_id]
            has_cancelled = True
    return has_cancelled


def store_message(message: Message) -> models.Message:
    """Parse a telegram message, store it in the database, and return it."""

    # add chat to database
    db.add_chat(utils.parse_chat(message.chat))
    # add topic to database
    if message.is_topic_message:
        db.add_topic(utils.parse_topic(message))
    # add user to database
    if user := message.from_user:
        db.add_user(utils.parse_user(user))
    # add sender chat to database
    if sender := message.sender_chat:
        db.add_chat(utils.parse_chat(sender))
    # add message to database and return it
    db.add_message(db_message := utils.parse_message(message))
    return db_message


async def reply_to_message(message: Message):
    """Reply to a message using a bot."""

    # set typing status
    topic_id: int = None  # type: ignore
    if message.is_topic_message and message.message_thread_id:
        topic_id = message.message_thread_id
    await message.chat.send_action(ChatAction.TYPING, topic_id)
    # set model and chat history
    model = ChatGPT()
    model.temperature = 1.25
    gpt_chat: GPTChat = _get_history(message.chat_id, topic_id)
    # gpt_chat.insert(0, bot_prompt)
    # stream the reply
    chatgpt = ChatCompletion(model)
    usage = await _stream_reply(chatgpt, message, gpt_chat)

    # count usage towards the user
    if user := db.get_user(message.from_user.id):
        user.usage = usage if not user.usage else user.usage + usage
        db.add_user(user)
    # count usage towards the chat if not a topic message
    if not topic_id:
        chat = db.get_chat(message.chat_id)
        chat.usage = usage if not chat.usage else chat.usage + usage
        db.add_chat(chat)
    # count usage towards the topic if a topic message
    else:
        topic = db.get_topic(topic_id, message.chat_id)
        topic.usage = usage if not topic.usage else topic.usage + usage
        db.add_topic(topic)


def _get_history(chat_id, topic_id) -> GPTChat:
    # load chat history from database
    db_messages = db.get_messages(chat_id, topic_id)
    # construct chatgpt messages
    chatgpt_messages: list[GPTMessage] = []
    has_system_message = False
    for db_message in db_messages:
        if not db_message.text:
            continue
        # construct system message
        if db_message.role == MessageRole.SYSTEM:
            chatgpt_messages.append(
                GPTMessage(
                    db_message.text, db_message.role, db_message.name or ""
                )
            )
            has_system_message = True
            continue
        # create metadata
        if db_message.user and db_message.user.username:
            username = db_message.user.username
            username = re.sub(r"^[^a-zA-Z0-9_-]{1,64}$", "", username)
        else:
            username = "unknown"
        metadata = f"{id}-{db_message.reply_id}-{username}"
        # create message and its metadata
        chatgpt_messages.append(GPTMessage(db_message.text, db_message.role))
        chatgpt_messages.append(GPTMessage(metadata, MessageRole.SYSTEM))

    # add default system message if none
    if not has_system_message:
        chatgpt_messages.insert(
            0,
            GPTMessage(
                # prompts[DEFAULT_PROMPT],
                MessageRole.SYSTEM
            ),
        )

    return GPTChat(chatgpt_messages)


async def _stream_reply(chat: ChatCompletion, message, history) -> int:
    global _requests
    # openai completion request
    request = chat.stream(history)
    # streamed output
    chatgpt_reply: GPTReply | None = None
    bot_message: Message | None = None

    # get the model reply and the bot message when ready
    logger.debug("streaming chatgpt reply...")
    try:  # stream the message
        chatgpt_reply, bot_message = await _stream_message(request, message)
    except Exception as e:
        await _handle_streaming_exception(e, bot_message)
    finally:  # cancel the model request
        if not bot_message:
            return 0
        await cancel_reply(bot_message)

    # store the reply in the database
    db_message = store_message(bot_message)
    db_message.role = chatgpt_reply.role
    db_message.finish_reason = chatgpt_reply.finish_reason
    db_message.text = str(chatgpt_reply)
    db_message.prompt_tokens = chatgpt_reply.prompt_tokens
    db_message.reply_tokens = chatgpt_reply.reply_tokens
    db.add_message(db_message)
    return db_message.prompt_tokens + db_message.reply_tokens


async def _stream_message(request: AsyncGenerator, message: Message):
    global _edit_timer, _requests

    reply = GPTReply("")
    bot_message: Message | None = None
    last_message = ""
    # send message packets in chunks
    chunk_size = 10
    chunk_counter = 0

    try:  # send the message chunks
        async for packet in request:
            chunk_counter += 1
            reply = packet if isinstance(packet, GPTReply) else reply
            # wait for the chunk to be filled
            if chunk_counter % chunk_size != 0:
                continue
            # send the chunk
            chunk_counter = 0
            bot_message, last_message = await _send_chunk(
                reply, bot_message or message, last_message, request
            )
    finally:
        # send the final message chunk
        bot_message, _ = await _send_chunk(
            reply, bot_message or message, last_message, request
        )
        return reply, bot_message


def _format_text(text: str) -> str:
    text = markdown((text))
    # constraints
    valid_tags = [
        "b",
        "strong",
        "i",
        "em",
        "u",
        "ins",
        "s",
        "strike",
        "del",
        "span",
        "a",
        "tg-emoji",
        "tg-spoiler",
        "code",
    ]
    valid_attrs = {
        "a": ["href"],
        "tg-emoji": ["emoji-id"],
        "span": ["class"],
    }
    # parse the text
    for tag in (html_soup := BeautifulSoup(text, "html.parser")).find_all():
        # replace reserved characters with HTML entities
        for string in tag.strings:
            string = html.escape(string)
        # remove the tag if it's not valid
        if tag.name not in valid_tags:
            tag.unwrap()
        else:  # remove the attribute if it's not valid
            for attr in tag.attrs.copy():
                if attr not in valid_attrs.get(tag.name, []):
                    del tag[attr]
    return str(html_soup)


def _get_request_id(message: Message) -> str:
    topic_id = None
    if message.is_topic_message:
        topic_id = message.message_thread_id
    return f"{message.chat.id}:{topic_id or ''}:{message.message_id}"


async def _send_chunk(reply, message: Message, last_message: str, request):
    # send the new message formatted as markdown
    html = _format_text(str(reply))
    if html == last_message:  # check if the message changed
        return message, last_message

    # send initial message
    if not message.from_user.is_bot:
        message = await message.reply_html(text=html)
        _requests[_get_request_id(message)] = request  # store request
        last_message = html
    else:  # update the bot message by editing it
        await asyncio.sleep(0.1)  # prevent flood wait error
        await message.edit_text(html, parse_mode=ParseMode.HTML)
        last_message = html
    return message, last_message


async def _handle_streaming_exception(e: Exception, bot_msg) -> None:
    msg = None
    try:
        if isinstance(e, ConnectionError):
            msg = "Connection to OpenAI lost..."
        elif isinstance(e, TokenLimitError):
            msg = "Context limit reached."
        elif isinstance(e, (CompletionError, TelegramError)):
            logger.error(f"streaming error: {e}")
            msg = "Error generating reply..."
        else:
            logger.error(f"unknown error: {e}")
            msg = "Unknown error encountered."
            raise e
    finally:
        if isinstance(bot_msg, Message) and msg:
            await bot_msg.reply_html(text=msg)
