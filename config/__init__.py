"""ChatGPT Telegram bot configuration."""

import os

import dotenv

dotenv.load_dotenv()

TOKEN = os.environ.get('TOKEN', '')
"""Telegram bot token."""
