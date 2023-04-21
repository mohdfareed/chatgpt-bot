"""ChatGPT Telegram bot configuration."""

import os

import dotenv

_root = os.path.dirname(os.path.abspath(__file__))
_passport_key = os.path.join(_root, 'passport.key')
dotenv.load_dotenv()


PASSPORT_KEY = open(_passport_key, "rb").read()
"""Passports authentication key."""

TOKEN = os.environ.get('TOKEN', '')
"""Telegram bot token."""

APPID = int(os.environ.get('APPID', '0'))
"""Application ID."""

APPID_HASH = os.environ.get('APPID_HASH', '')
"""Application ID hash."""

SESSIONS = os.path.join(_root, 'sessions')
"""Sessions directory."""
os.makedirs(SESSIONS, exist_ok=True)


def session_path(session: str) -> str:
    """Returns the path to a session file.

    Args:
        session_id (int): The session name.

    Returns:
        str: The path to the session file.
    """
    return os.path.join(SESSIONS, f'{session}')
