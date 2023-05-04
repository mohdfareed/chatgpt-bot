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
Chat messages are formatted as '[<message_id>]<username>: <message>'.
Your messages will not include the message ID or username.
Your messages must be in the following Markdown format:
*bold text* _italic text_ __underline__ ~strikethrough~ ||spoiler||
[inline URL](http://www.example.com/) @username `inline and block code`
"""
bot_prompt = GPTMessage(GPTMessage.Role.SYSTEM, bot_prompt)

if not BOT_TOKEN:
    raise ValueError("'BOT_TOKEN' environment variable not set")
