"""The bot's core functionality and Telegram callbacks."""

import asyncio
import html
import re
import time

from bs4 import BeautifulSoup
from chatgpt.chat import Chat as GPTChat
from chatgpt.completions import ChatCompletion as GPTCompletion
from chatgpt.completions import CompletionError, FinishReason
from chatgpt.messages import Message as GPTMessage
from chatgpt.messages import Reply as GPTReply
from telegram import Message
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import ExtBot

from chatgpt_bot import DEFAULT_PROMPT, bot_prompt, logger, prompts, utils
from database import models
from database import utils as db

_edit_timer = .0
"""Timer since the last edit message request."""


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


async def reply_to_message(message: Message, bot: ExtBot):
    """Reply to a message using a bot."""

    # bot message arguments
    message_args = {}
    message_args['chat_id'] = message.chat_id
    message_args['reply_to_message_id'] = message.message_id
    message_args['message_thread_id'] = None
    message_args['parse_mode'] = ParseMode.HTML
    if message.is_topic_message and message.message_thread_id:
        message_args['message_thread_id'] = message.message_thread_id

    # set typing status
    await bot.send_chat_action(
        chat_id=message_args['chat_id'],
        message_thread_id=message_args['message_thread_id'],  # type: ignore
        action=ChatAction.TYPING
    )

    # set chat history
    gpt_chat = _get_history(
        message.chat_id,
        message_args['message_thread_id']
    )
    gpt_chat.history.insert(0, bot_prompt)

    try:  # stream the reply
        chatgpt = GPTCompletion()
        chatgpt.temperature = 1.25
        context = gpt_chat.to_messages()
        usage = await _request_completion(chatgpt, bot, context, message_args)
    except CompletionError as e:
        logger.error(f"completion stream error replying to message: {e}")
        raise
    except TelegramError as e:
        logger.error(f"telegram error replying to message: {e}")
        raise
    except Exception as e:
        logger.error(f"error replying to message: {e}")
        raise

    # count usage towards the user
    if user := db.get_user(message.from_user.id):
        user.usage = usage if not user.usage else user.usage + usage
        db.add_user(user)
    # count usage towards the topic, if any
    if topic_id := message_args['message_thread_id']:
        if topic := db.get_topic(topic_id, message.chat_id):
            topic.usage = usage if not topic.usage else topic.usage + usage
            db.add_topic(topic)
    else:  # count usage towards the chat if no topic
        chat = db.get_chat(message.chat_id)
        chat.usage = usage if not chat.usage else chat.usage + usage
        db.add_chat(chat)


def _get_history(chat_id, topic_id) -> GPTChat:
    # load chat history from database
    messages = db.get_messages(chat_id, topic_id)
    ids = {}  # map of local message ids to global message ids
    id = 0  # id counter

    # construct chatgpt messages
    chatgpt_messages: list[GPTMessage] = []
    has_system_message = False
    for message in messages:
        if not message.text:
            continue

        # construct system message
        if message.role == GPTMessage.Role.SYSTEM:
            chatgpt_messages.append(GPTMessage(
                message.role,
                message.text,
                message.name or ''
            ))
            has_system_message = True
            continue

        # create metadata
        ids[message.id] = (id := id+1)
        try:  # add reply id to metadata
            reply_id = ids[message.reply_id]
        except KeyError:
            reply_id = 0
        # add username to metadata
        if message.user and message.user.username:
            username = message.user.username
            username = re.sub(r'^[^a-zA-Z0-9_-]{1,64}$', '', username)
        else:
            username = 'unknown'
        metadata = f"{id}-{reply_id}-{username}"

        # create message
        chatgpt_messages.append(GPTMessage(
            message.role,
            message.text,
            name=metadata
        ))

    # add default system message if none
    if not has_system_message:
        chatgpt_messages.insert(0, GPTMessage(
            GPTMessage.Role.SYSTEM,
            prompts[DEFAULT_PROMPT]
        ))

    return GPTChat(chatgpt_messages)


async def _request_completion(model: GPTCompletion, bot: ExtBot,
                              chat_history, message_args) -> int:
    # openai completion request and bot message
    request = model.async_request(chat_history)
    bot_message: Message = None  # type: ignore
    chatgpt_reply: GPTReply = None  # type: ignore
    text: str = None  # type: ignore

    # get the model reply and the bot message when ready
    logger.debug('streaming chatgpt reply...')
    try:  # stream the message
        args = request, bot, message_args
        chatgpt_reply, bot_message, text = await _stream_message(*args)
    except Exception as e:
        logger.error(f"error streaming chatgpt reply: {e}")
        raise
    finally:  # cancel the model request
        model.cancel()
        # store the bot's reply message if sent
        if bot_message:
            db_message = store_message(bot_message)
            db_message.role = GPTMessage.Role.CHATGPT
            db_message.finish_reason = FinishReason.UNDEFINED
            db.add_message(db_message)
            # fill in message text if generated
            if text:
                db_message.text = text
            db.add_message(db_message)
            # fill-in chatgpt reply fields if generated
            if not chatgpt_reply:
                db_message.finish_reason = chatgpt_reply.finish_reason
                db_message.prompt_tokens = chatgpt_reply.prompt_tokens
                db_message.reply_tokens = chatgpt_reply.reply_tokens
            # store message and return completion usage
                db.add_message(db_message)
                return db_message.prompt_tokens + db_message.reply_tokens
    return 0


async def _stream_message(request, bot: ExtBot, message_args):
    global _edit_timer

    chatgpt_reply: GPTReply = None  # type: ignore
    bot_message: Message = None  # type: ignore
    # send message packets in chunks
    chunk_size = 10
    chunk_counter = 0
    message_text = ''
    chunk = ''

    async for packet in request:
        # flush when the model reply is ready
        if flush := isinstance(packet, GPTReply):
            chatgpt_reply = packet
        else:
            chunk_counter += 1
            chunk += packet
        # wait for the chunk to be filled
        if not flush and chunk_counter % chunk_size != 0:
            continue
        # send the message chunk formatted as markdown
        message_text += chunk
        html = _format_text(message_text)

        if chunk and not bot_message:  # send initial message
            bot_message = await bot.send_message(**message_args, text=html)
        elif chunk:  # edit message if new chunk was received
            # TODO: prevent flood wait errors
            if (elapsed_time := time.monotonic() - _edit_timer) < 0.1:
                await asyncio.sleep(0.1 - elapsed_time)
            _edit_timer = time.monotonic()
            # edit the bot message
            await bot_message.edit_text(
                text=html, parse_mode=message_args['parse_mode']
            )

        chunk_counter = 0
        chunk = ''

    return chatgpt_reply, bot_message, message_text


def _format_text(text: str) -> str:
    # constraints
    valid_tags = ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del',
                  'span', 'a', 'tg-emoji', 'tg-spoiler', 'code']
    valid_attrs = {
        'a': ['href'],
        'tg-emoji': ['emoji-id'],
        'span': ['class'],
    }
    # parse the text
    for tag in (html_soup := BeautifulSoup(text, 'html.parser')).find_all():
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
