"""Database core functionality."""

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists

from database import DATABASE, URL, USERNAME, logger
from database.models import Base

_container: Container = None  # type: ignore
_engine: Engine = None  # type: ignore

session_maker: sessionmaker = None  # type: ignore
"""The database session maker."""


def start():
    """Initialize database by setting up a Docker container."""
    global _engine, session_maker

    logger.info("initializing database...")
    try:  # setup docker container
        _setup_container()
    except DockerException:
        raise RuntimeError("failed to setup docker container")

    # initialize database
    _engine = create_engine(URL)
    while not database_exists(URL):
        pass  # wait for database to start up

    # create missing tables and session maker
    Base.metadata.create_all(_engine)
    session_maker = sessionmaker(bind=_engine)
    logger.info("database initialized")


def stop():
    """Stop the database engine and container."""
    global _container, _engine

    # dispose of database connections
    _engine.dispose() if _engine else None
    # stop the database container
    _container.stop() if _container else None

    logger.info("database has stopped")


def backup():
    """Backup database to file."""
    global _container

    validate_connection()
    command = f"pg_dump -U {USERNAME} -d {DATABASE} > /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("backup failed")
    logger.info("database backed up")


def restore():
    """Load database from backup file."""
    global _container

    validate_connection()
    command = f"psql -U {USERNAME} -d {DATABASE} < /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("restoration failed")
    logger.info("database restored")


def validate_connection():
    """Check if the database is connected."""
    global _container, _engine, session_maker

    # check if engine and container are initialized
    if None in (session_maker, _container, _engine):
        raise RuntimeError("database not initialized")
    # check connection to database
    if not database_exists(_engine.url):
        raise RuntimeError("failed to connect to database")


def _setup_container():
    """Start the database container."""
    from database import CONTAINER_NAME, backup_path, container_config
    global _container

    # create database backup file
    with open(backup_path, 'a'):
        pass

    # connect to docker and start container
    client = docker.from_env()
    try:  # get existing container and start it
        _container = client.containers.get(CONTAINER_NAME)  # type: ignore
        _container.start() if _container.status != 'running' else None
    except NotFound:  # run new container otherwise
        logger.info("creating database container...")
        _container = client.containers.run(**container_config)  # type: ignore
