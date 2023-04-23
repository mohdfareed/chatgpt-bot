"""ChatGPT based Telegram bot."""

import os

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN', '')
"""Telegram bot token."""

if not TOKEN:
    raise ValueError("'BOT_TOKEN' environment variable not set")
