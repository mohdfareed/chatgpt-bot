"""ChatGPT database controller package."""

import logging
import os

from dotenv import load_dotenv

_root = os.path.dirname(os.path.realpath(__file__))
load_dotenv()

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

logger = logging.getLogger(__name__)
"""The database logger."""

# docker database container configuration
backup_path = os.path.join(_root, 'chatgpt_db.sql')
container_config = {
    'image': IMAGE_NAME,
    'name': CONTAINER_NAME,
    'environment': {
        'POSTGRES_USER': USERNAME,
        'POSTGRES_PASSWORD': PASSWORD,
        'POSTGRES_DB': DATABASE,
    },
    'volumes': {backup_path: {'bind': f'/backup.sql'}},
    'ports': {'5432': 5432},
    'detach': True  # run container in background
}

# validate database environment variables
if not all([USERNAME, PASSWORD, DATABASE]):
    raise ValueError("environment variables not set")
