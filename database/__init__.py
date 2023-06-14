"""ChatGPT database controller package."""

import logging as logging
import os as os

import sqlalchemy as sql
import sqlalchemy_utils as sql_utils
from cryptography import fernet
from sqlalchemy_utils.types.encrypted import encrypted_type

_root = os.path.abspath(os.path.dirname(__file__))
_key_file = os.path.join(_root, "database.key")
_db_file = os.path.join(_root, "database.db")

logger = logging.getLogger(__name__)
"""The database logger."""
url = os.environ.get("DATABASE_URL") or f"sqlite:///{_db_file}"
"""The database URL."""
encryption_key = bytes(os.environ.get("ENCRYPTION_KEY", ""), "utf-8")
"""The database encryption key."""

# set encryption key if not provided
if not encryption_key:
    # generate encryption key if not found
    if not os.path.exists(_key_file):
        logger.warning("Generating new encryption key")
        with open(_key_file, "wb") as _file:
            _file.write(fernet.Fernet.generate_key())
    # read encryption key from file
    encryption_key = open(_key_file, "rb").read()

from .core import *
from .models import *
