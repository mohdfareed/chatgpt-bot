"""ChatGPT database controller package."""

import logging
import os

# postgres database
URL = os.environ.get('DATABASE_URL', '')
"""The database URL."""

if not URL:
    raise ValueError("'DATABASE_URL' environment variables not set")

logger = logging.getLogger(__name__)
"""The database logger."""
