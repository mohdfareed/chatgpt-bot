"""ChatGPT database controller package."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()
_root = os.path.dirname(os.path.realpath(__file__))
"""The root directory of the database package."""
_backup_path = os.path.join(_root, 'chatgpt_db.sql')
"""The database backup file path."""
logger: logging.Logger = logging.getLogger(__name__)
"""The database logger."""

# postgres
USERNAME = os.getenv('DATABASE_USER', '')
"""The database user."""
PASSWORD = os.getenv('DATABASE_PASSWORD', '')
"""The database password."""
DATABASE = os.getenv('DATABASE_NAME', '')
"""The database name."""
URL = f"postgresql://{USERNAME}:{PASSWORD}@localhost/{DATABASE}"
"""The database URL."""

# docker
IMAGE_NAME = 'postgres:latest'  # official postgres image
"""The Docker image name."""
CONTAINER_NAME = 'chatgpt-db'
"""The Docker container name."""

# container configuration
container_config = {
    'image': IMAGE_NAME,
    'name': CONTAINER_NAME,
    'environment': {
        'POSTGRES_USER': USERNAME,
        'POSTGRES_PASSWORD': PASSWORD,
        'POSTGRES_DB': DATABASE,
    },
    'volumes': {_backup_path: {'bind': f'/backup.sql'}},
    'ports': {'5432': 5432},
    'detach': True  # run container in background
}

# validate environment variables
if not all([USERNAME, PASSWORD, DATABASE]):
    raise ValueError("environment variables not set")
