"""ChatGPT database controller package."""

import logging
import os

# postgres database
URL = os.environ.get('DATABASE_URL', '')
print(URL)
"""The database URL."""

logger = logging.getLogger(__name__)
"""The database logger."""

if not URL:
    raise ValueError("'DATABASE_URL' environment variables not set")
