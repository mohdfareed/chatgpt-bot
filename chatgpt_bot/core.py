"""The bot's core functionality and Telegram callbacks."""

from chatgpt.chat import Chat as GPTChat
from chatgpt.completions import ChatCompletion
from chatgpt.message import Message as GPTMessage
from chatgpt.message import Prompt as GPTPrompt
from telegram import Message, Update
from telegram.ext import ContextTypes, ExtBot

from chatgpt_bot import logger
from chatgpt_bot.utils import store_message, stream_completion
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
    store_message(message)


async def mention_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    logger.info("mention_callback")
    if not (message := update.effective_message):
        return
    store_message(message)

    if not message.text:
        return
    if context.bot.username not in message.text:
        return

    await send_reply(message, context.bot)


async def private_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a message."""

    logger.info("private_callback")
    if not (message := update.effective_message):
        return
    if not message.text:
        return

    store_message(message)
    await send_reply(message, context.bot)


async def send_reply(message: Message, bot: ExtBot):
    """Reply to a message."""

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
    chatgpt = ChatCompletion()

    try:  # stream the reply
        usage = await stream_completion(chatgpt, bot, context, message_args)
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
