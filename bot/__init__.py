"""ChatGPT based Telegram bot."""

import logging as _logging

logger = _logging.getLogger(__name__)
"""The bot logger."""

from .core import run
