"""Database core functionality. It is responsible for managing the database
within a Docker container."""

from docker.models.containers import Container
from sqlalchemy import Engine
from sqlalchemy_utils import database_exists

from database import DATABASE, USERNAME, logger

_container: Container
engine: Engine
"""The database engine."""


def start(clean: bool = False) -> None:
    """Initialize the database in a Docker container.

    Args:
        clean: Whether to remove the existing database container.

    Raises:
        RuntimeError: If the database container fails to start.
    """
    from docker.errors import DockerException
    from sqlalchemy import create_engine

    from database import URL
    from database.models import Base
    global engine

    logger.info("initializing database...")
    try:  # setup docker container
        _setup_container(clean)
    except DockerException:
        raise RuntimeError("failed to setup docker container")

    # initialize database
    engine = create_engine(URL)
    while not database_exists(URL):
        pass  # wait for database to start up

    # restore database from backup and initialize tables
    restore() if not clean else None
    Base.metadata.create_all(engine)


def stop() -> None:
    """Backup and stop the database engine and container."""
    global _container, engine

    try:  # try to backup database
        backup()
    except ConnectionError:
        pass  # ignore if database is not connected

    # dispose of database connections
    engine.dispose() if engine else None
    # stop the database container
    _container.stop() if _container else None

    logger.info("database has stopped")


def backup() -> None:
    """Backup database to file.

    Raises:
        RuntimeError: If the backup fails.
        ConnectionError: If the database is not connected.
    """
    global _container

    validate_connection()
    command = f"pg_dump -U {USERNAME} -d {DATABASE} > /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("backup failed")
    logger.info("database backed up")


def restore() -> None:
    """Load database from backup file.

    Raises:
        RuntimeError: If the restoration fails.
        ConnectionError: If the database is not connected.
    """
    global _container

    validate_connection()
    command = f"psql -U {USERNAME} -d {DATABASE} < /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("restoration failed")
    logger.info("database restored")


def validate_connection() -> None:
    """Check if the database is connected.

    Raises:
        ConnectionError: If the database is not connected.
    """
    global _container, engine

    # check if engine and container are initialized
    if None in (_container, engine):
        raise ConnectionError("database not initialized")
    # check connection to database
    if not database_exists(engine.url):
        raise ConnectionError("failed to connect to database")


def _setup_container(clean):
    """Start the database container."""
    import docker
    from docker.errors import NotFound

    from database import CONTAINER_NAME, backup_path, container_config
    global _container

    # create database backup file
    with open(backup_path, 'a'):
        pass

    # connect to docker and start container
    client = docker.from_env()
    try:  # get existing container
        _container = client.containers.get(CONTAINER_NAME)  # type: ignore

        if not clean:  # start existing container
            _container.start() if _container.status != 'running' else None
        else:  # remove existing container
            _container.remove(force=True)
            raise NotFound("container removed")

    except NotFound:  # run new container otherwise
        logger.info("creating database container...")
        _container = client.containers.run(**container_config)  # type: ignore
