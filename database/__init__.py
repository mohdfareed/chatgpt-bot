"""ChatGPT database controller package."""

import logging
import os

_root = os.path.dirname(os.path.realpath(__file__))

# postgres
_PASSWORD = os.environ.get('DB_PASSWORD', '')
"""The database password."""
DATABASE = 'chatgpt-db'
"""The database name."""
USERNAME = 'chatgpt'
"""The database user."""
URL = f"postgresql://{USERNAME}:{_PASSWORD}@localhost/{DATABASE}"
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
container_config = dict(
    image=IMAGE_NAME,
    name=CONTAINER_NAME,
    environment=dict(
        POSTGRES_DB=DATABASE,
        POSTGRES_USER=USERNAME,
        POSTGRES_PASSWORD=_PASSWORD
    ),
    volumes={backup_path: dict(bind=f'/backup.sql')},
    ports={'5432': 5432},
    detach=True  # run container in background
)

if not _PASSWORD:
    raise ValueError("'DB_PASSWORD' environment variable not set")
