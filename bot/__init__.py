"""ChatGPT based Telegram bot."""

import logging
import os

import requests

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
"""The environment's Serper API key for Google search."""

logger = logging.getLogger(__name__)
"""The bot logger."""
token = os.getenv("TELEGRAM_BOT_TOKEN") or ""
"""Telegram bot token."""
webhook = os.getenv("WEBHOOK") or ""
"""Telegram webhook URL (external address)."""
webhook_addr = os.getenv("WEBHOOK_ADDR") or "localhost"
"""Telegram webhook IP address."""
webhook_port = int(os.getenv("WEBHOOK_PORT") or 80)
"""Telegram webhook port."""
webhook_path = os.getenv("WEBHOOK_PATH") or ""
"""Telegram webhook path."""
dev_mode = not webhook
"""Whether the bot is running in development mode (polling mode)."""

# validate token
_url = f"https://api.telegram.org/bot{token}/getMe"
if requests.get(_url).status_code != 200:  # invalid token
    raise ValueError(f"Invalid Telegram bot token: {token}")
