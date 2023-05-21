"""ChatGPT based Telegram bot."""

import logging
import os

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
"""Telegram bot token."""
WEBHOOK = os.getenv('WEBHOOK', '')
"""Telegram webhook URL."""
WEBHOOK_ADDR = os.getenv('WEBHOOK_ADDR', '')
"""Telegram webhook IP address."""
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '-1'))
"""Telegram webhook port."""
DEV = False
"""Whether the bot is running in development mode."""

if not BOT_TOKEN:
    raise ValueError("environment variables not set")
if not all([WEBHOOK_ADDR, (False if WEBHOOK_PORT < 0 else True), WEBHOOK]):
    DEV = True

logger: logging.Logger = logging.getLogger(__name__)
"""The bot logger."""
