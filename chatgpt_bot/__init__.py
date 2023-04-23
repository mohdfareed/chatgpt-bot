"""ChatGPT based Telegram bot."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
"""Telegram bot token."""
OPENAI_KEY = os.getenv('OPENAI_KEY', '')
"""OpenAI API key."""

logger: logging.Logger = logging.getLogger(__name__)
"""The bot logger."""

if not BOT_TOKEN:
    raise ValueError("'BOT_TOKEN' environment variable not set")
