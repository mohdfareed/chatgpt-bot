"""ChatGPT based Telegram bot."""

import logging as _logging
import os as _os

import requests as _requests

logger: _logging.Logger = _logging.getLogger(__name__)
"""The bot logger."""
token = _os.getenv("TELEGRAM_BOT_TOKEN") or ""
"""Telegram bot token."""
webhook = _os.getenv("WEBHOOK") or ""
"""Telegram webhook URL."""
webhook_addr = _os.getenv("WEBHOOK_ADDR") or ""
"""Telegram webhook IP address."""
webhook_port = int(_os.getenv("WEBHOOK_PORT") or -1)
"""Telegram webhook port."""
dev_mode = not (webhook and webhook_addr and (webhook_port > -1))
"""Whether the bot is running in development mode (polling mode)."""


# validate token
if not token:
    raise ValueError("Environment variable 'TELEGRAM_BOT_TOKEN' is not set.")
url = f"https://api.telegram.org/bot{token}/getMe"
if _requests.get(url).status_code != 200:  # invalid token
    raise ValueError(f"Invalid Telegram bot token: {token}")

# log webhook settings
if not dev_mode:
    logger.info(f"Using webhook: {webhook} [{webhook_addr}:{webhook_port}]")
else:
    logger.warning("Running in development mode.")
