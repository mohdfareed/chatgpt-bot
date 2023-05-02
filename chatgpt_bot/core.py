"""The bot's core functionality and Telegram callbacks."""

from chatgpt.chat import Chat as GPTChat
from chatgpt.completions import ChatCompletion as GPTCompletion
from chatgpt.message import Message as GPTMessage
from chatgpt.message import Prompt as GPTPrompt
from chatgpt.message import Reply as GPTReply
from telegram import Message
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import ExtBot

from chatgpt_bot import logger, utils
from database import models
from database import utils as db


async def reply_to_message(message: Message, bot: ExtBot):
    """Reply to a message using a bot."""

    # bot message arguments
    message_args = {
        'chat_id': message.chat_id,
        'reply_to_message_id': message.message_id,
        'text': ''
    }

    # set prompt
    sys_prompt = """
    You are a friendly member of a chat group. You will talk as yourself. Be
    genuine and transparent. You will not be judged for your opinions. You
    will act as a person who is talking with their friends.
    """

    # set context
    chat_messages: list[GPTMessage] = [
        GPTPrompt(GPTPrompt.Role.SYSTEM, sys_prompt),
        GPTPrompt(GPTPrompt.Role.USER,
                  message.text.replace(f"@{bot.username}", '')),
    ]
    context = GPTChat(messages=chat_messages).to_messages()

    # set message
    if message.is_topic_message and message.message_thread_id:
        message_args['message_thread_id'] = message.message_thread_id
    # set chatgpt instance
    chatgpt = GPTCompletion()

    try:  # stream the reply
        usage = await _request_completion(chatgpt, bot, context, message_args)
    except Exception as e:
        chatgpt.cancel()  # cancel the request if it hasn't already finished
        raise RuntimeError(f"error streaming message: {e}")

    # count usage towards the user
    if user := db.get_user(message.from_user.id):
        user.usage += usage
        db.add_user(user)
    # count usage towards the chat
    if chat := db.get_chat(message.chat_id):
        chat.usage += usage
        db.add_chat(chat)
    # count usage towards the topic, if any
    if topic_id := message_args.get('message_thread_id', None):
        if topic := db.get_topic(message.chat_id, topic_id):
            topic.usage += usage
            db.add_topic(topic)


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


async def _request_completion(model: GPTCompletion, bot: ExtBot,
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
    db.add_message(db_message)
    return db_message.prompt_tokens + db_message.reply_tokens


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

        # set typing status if not flushing
        await bot.send_chat_action(
            chat_id=message_args['chat_id'],
            message_thread_id=message_args.get('message_thread_id', None),
            action=ChatAction.TYPING
        ) if not flush else None
        chunk_counter = 0

    # finish typing
    return chatgpt_reply, bot_message
