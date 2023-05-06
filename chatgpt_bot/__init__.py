"""ChatGPT based Telegram bot."""

import logging
import os

from chatgpt.messages import Message as GPTMessage
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
"""Telegram bot token."""
OPENAI_KEY = os.getenv('OPENAI_KEY', '')
"""OpenAI API key."""

logger: logging.Logger = logging.getLogger(__name__)
"""The bot logger."""

bot_prompt = """
Mention a user with '@username'.
Only the following syntax is allowed:
*bold* _italic_ ~strikethrough~ ||spoiler|| `code`
[inline URL](http://www.example.com/)

You have access to the chat history, with the following metadata embedded:
<MessageID>-<InReplyToID>---<Username>
The `<InReplyToID>` is the ID of the message to which the message is replying.
It is `0` if the message is not a reply or it doesn't exist.
"""
bot_prompt = GPTMessage(GPTMessage.Role.SYSTEM, bot_prompt)

if not BOT_TOKEN:
    raise ValueError("'BOT_TOKEN' environment variable not set")
