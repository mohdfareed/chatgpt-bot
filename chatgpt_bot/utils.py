"""Utility and helper functions for mapping OpenAI and Telegram objects to
database objects."""

from chatgpt.completions import ChatCompletion as GPTCompletion
from chatgpt.message import Reply as GPTReply
from telegram import Chat, Message, User
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import ExtBot

from chatgpt_bot import logger
from database import models
from database.utils import add_chat, add_message, add_topic, add_user


async def stream_completion(model: GPTCompletion, bot: ExtBot,
                            chat_history, message_args: dict) -> int:
    """Stream a telegram message using a ChatGPT model and return the generated
    message. The bot message is sent with the provided `message_args`, which
    must include the `chat_id`."""

    # openai completion request
    request = model.async_request(chat_history)
    # get the model reply and the bot message when ready
    logger.info('streaming chatgpt reply...')
    try:  # stream the message
        args = request, bot, message_args
        chatgpt_reply, bot_message = await _stream_message(*args)
    except:  # cancel the model request
        model.cancel()
        raise

    # store the bot's reply message
    db_message = store_message(bot_message)
    # fill-in chatgpt reply fields
    db_message.role = chatgpt_reply.role
    db_message.finish_reason = chatgpt_reply.finish_reason
    db_message.prompt_tokens = chatgpt_reply.prompt_tokens
    db_message.reply_tokens = chatgpt_reply.reply_tokens
    # store message and return completion usage
    add_message(db_message)
    return db_message.prompt_tokens + db_message.reply_tokens


def store_message(message: Message) -> models.Message:
    """Parse a telegram message, store it in the database, and return it."""

    # add chat to database
    add_chat(parse_chat(message.chat))
    # add topic to database
    if message.is_topic_message:
        add_topic(parse_topic(message))
    # add user to database
    if user := message.from_user:
        add_user(parse_user(user))
    # add sender chat to database
    if sender := message.sender_chat:
        add_chat(parse_chat(sender))

    # add message to database and return it
    add_message(db_message := parse_message(message))
    return db_message


def parse_message(message: Message) -> models.Message:
    """Parse a telegram update message into a database message."""
    db_message = models.Message()

    # create message
    db_message.id = message.message_id
    db_message.chat_id = message.chat_id
    # fill-in the topic if any
    if message.is_topic_message and message.message_thread_id:
        db_message.topic_id = message.message_thread_id
    # fill-in the user if any
    if user := message.from_user:
        db_message.user_id = user.id
    # fill-in reply message if any
    if reply := message.reply_to_message:
        if message.is_topic_message:
            # don't include the reply if it's the topic creation message
            if reply.message_id != message.message_thread_id:
                db_message.reply_id = reply.message_id
        else:
            db_message.reply_id = reply.message_id
    # fill-in the text if any
    if text := message.text:
        db_message.text = text

    return db_message


def parse_chat(chat: Chat) -> models.Chat:
    """Parse a telegram update chat into a database chat."""
    db_chat = models.Chat()

    # create chat
    db_chat.id = chat.id

    return db_chat


def parse_topic(message: Message) -> models.Topic:
    """Parse a telegram update message into a database topic."""
    db_topic = models.Topic()

    # create a topic if any
    if topic_id := message.message_thread_id:
        db_topic.id = topic_id
        db_topic.chat_id = message.chat_id

    return db_topic


def parse_user(user: User) -> models.User:
    """Parse a telegram update user into a database user."""
    db_user = models.User()

    # create user
    db_user.id = user.id
    db_user.username = user.username

    return db_user


async def _stream_message(request, bot, message_args):
    chatgpt_reply: GPTReply = None  # type: ignore
    bot_message: Message = None  # type: ignore

    # send packets in chunks
    chunk_size = 10
    chunk_counter = 0
    message_args['text'] = ''

    async for packet in request:
        # flush when the model reply is ready
        if flush := isinstance(packet, GPTReply):
            chatgpt_reply = packet
        else:
            message_args['text'] += packet

        # parse the packet
        chunk_counter += 1
        if not flush and chunk_counter % chunk_size != 0:
            continue

        # send the chunk
        if not bot_message:
            bot_message = await bot.send_message(**message_args)
        else:  # edit the message if one was received
            try:
                await bot_message.edit_text(text=message_args['text'])
            except TelegramError:
                pass

        # set typing status
        await bot.send_chat_action(
            chat_id=message_args['chat_id'],
            message_thread_id=message_args.get('message_thread_id', None),
            action=ChatAction.TYPING
        )
        chunk_counter = 0

    # finish typing
    return chatgpt_reply, bot_message
