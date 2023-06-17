"""ChatGPT database controller package."""

import logging as logging
import os as os

from cryptography import fernet

_root = os.path.abspath(os.path.dirname(__file__))
_key_file = os.path.join(_root, "database.key")
_db_file = os.path.join(_root, "database.db")

logger = logging.getLogger(__name__)
"""The database logger."""
url = os.environ.get("DATABASE_URL") or f"sqlite:///{_db_file}"
"""The database URL."""
encryption_key = bytes(os.environ.get("ENCRYPTION_KEY", ""), "utf-8")
"""The database encryption key."""

if not encryption_key:  # set encryption key if not provided
    if not os.path.exists(_key_file):  # generate key if not found
        logger.warning("Generating new encryption key")
        with open(_key_file, "wb") as _file:
            _file.write(fernet.Fernet.generate_key())
    # read encryption key from file
    encryption_key = open(_key_file, "rb").read()


from . import core as core
from . import models as models
