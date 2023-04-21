"""ChatGPT Telegram bot configuration."""

import os

from dotenv import load_dotenv

_key_filepath = os.path.join(os.path.dirname(__file__), 'passport.key')
load_dotenv()

PASSPORT_KEY = open(_key_filepath, "rb").read()
"""Passports authentication key."""
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
"""Telegram bot token."""
APPID = int(os.environ.get('TELEGRAM_APPID', '0'))
"""Application ID."""
APPID_HASH = os.environ.get('TELEGRAM_APPID_HASH', '')
"""Application ID hash."""
