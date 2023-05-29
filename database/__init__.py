"""ChatGPT database controller package."""

import logging as _logging
import os as _os

logger = _logging.getLogger(__name__)
"""The database logger."""

_db_path = _os.path.abspath(_os.path.dirname(__file__))
_default_url = f"sqlite:///{_db_path}/database.db"  # default sqlite database
url = _os.environ.get("DATABASE_URL") or _default_url
"""The database URL."""

logger.info(f"Using database at: {url}")
