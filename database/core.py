"""Database core functionality."""

import os

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists

from database import DATABASE, USERNAME, logger
from database.models import Base

_container: Container = None  # type: ignore
_engine: Engine = None  # type: ignore

session_maker: sessionmaker = None  # type: ignore
"""The database session maker."""


def start():
    """Initialize database by setting up a Docker container."""
    global _container, _engine, session_maker
    from database import URL

    # attach to docker and start container
    logger.info("initializing database...")
    try:  # check if docker is running
        client = docker.from_env()  # docker client
        _container = _start_container(client)
    except DockerException:
        raise RuntimeError("could not connect to docker")

    # initialize database
    _engine = create_engine(URL)
    # wait for database to start up
    while not database_exists(URL):
        pass
    # create tables if they don't exist
    Base.metadata.create_all(_engine)
    # initialized session
    session_maker = sessionmaker(bind=_engine)
    logger.info("database initialized")


def stop():
    """Stop the database engine and container."""
    global _container, _engine

    try:
        _engine.dispose()  # dispose of database connections
        _container.stop()  # stop the database container
    except:
        pass
    logger.info("database has stopped")


def backup():
    """Backup database to file."""
    global _container

    _verify_connection()
    logger.info("backing up...")
    command = f"pg_dump -U {USERNAME} -d {DATABASE} > /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("backup failed")


def restore():
    """Load database from backup file."""
    global _container

    _verify_connection()
    logger.info("restoring backup...")
    command = f"psql -U {USERNAME} -d {DATABASE} < /backup.sql"
    if _container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("restoration failed")


def _start_container(client: docker.DockerClient) -> Container:
    """Start the database container."""
    from database import CONTAINER_NAME as NAME
    from database import _backup_path, container_config

    # create database backup file
    with open(_backup_path, 'a'):
        pass

    container: Container
    try:  # get existing container and start it
        container = client.containers.get(NAME)  # type: ignore
        container.start() if container.status != 'running' else None
    except NotFound:  # run new container otherwise
        logger.info("starting database container...")
        container = client.containers.run(**container_config)  # type: ignore
    return container


def _verify_connection():
    """Check if the database is connected."""
    global _container, _engine, session_maker

    try:  # check if engine and container are defined
        _container.status
        _engine.url
    except:
        raise RuntimeError("database not initialized")

    if not database_exists(_engine.url):  # check connection
        raise RuntimeError("failed to connect to database")
    if session_maker is None:  # initialize session
        session_maker = sessionmaker(bind=_engine)
