"""Database core functionality."""

from random import random

import docker
from docker.errors import DockerException, NotFound
from docker.models.containers import Container
from sqlalchemy import Engine, create_engine
from sqlalchemy_utils import database_exists

from database import DATABASE, USERNAME, logger

container: Container
"""The database container."""
engine: Engine
"""The database engine."""


def start():
    """Initialize database by setting up a Docker container."""
    global container, engine
    from database import URL

    # attach to docker and start container
    logger.info("initializing database...")
    try:  # check if docker is running
        client = docker.from_env()  # docker client
    except DockerException:
        raise RuntimeError("could not connect to docker")
    container = _start_container(client)

    # initialize database
    engine = create_engine(URL)
    # wait for database to start up
    while not database_exists(URL):
        pass
    logger.info("database initialized")


def restore():
    """Load database from backup file."""
    global container

    _verify_connection()
    logger.info("restoring backup...")
    command = f"psql -U {USERNAME} -d {DATABASE} < /backup.sql"
    if container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("restoration failed")


def backup():
    """Backup database to file."""
    global container

    _verify_connection()
    logger.info("backing up...")
    command = f"pg_dump -U {USERNAME} -d {DATABASE} > /backup.sql"
    if container.exec_run(f"sh -c '{command}'").exit_code != 0:
        raise RuntimeError("restoration failed")


def stop():
    """Stop the database engine and container."""
    global container, engine

    engine.dispose()  # dispose of database connections
    container.stop()  # stop the database container
    logger.info("database has stopped")


def dummy_entries():
    global engine
    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker

    base = declarative_base()

    class DummyTable(base):
        # define the table schema
        __tablename__ = "dummy_table"
        id = Column(Integer, primary_key=True)
        name = Column(String)
        value = Column(Integer)

    # create the database tables
    base.metadata.create_all(engine)
    # create a session for interacting with the database
    Session = sessionmaker(bind=engine)
    session = Session()

    # insert some dummy data into the table
    session.add_all([
        DummyTable(name="foo", value=random() * 100),
        DummyTable(name="bar", value=random() * 100),
    ])
    session.commit()

    # retrieve data from the table and print it
    query = session.query(DummyTable).all()
    for row in query:
        print(f"{row.id} - {row.name}: {row.value}")
    session.close()  # close the session


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
    global container, engine

    try:  # check if engine and container are defined
        container.status
        engine.url
    except:
        raise RuntimeError("database not initialized")

    if not database_exists(engine.url):  # check connection
        raise RuntimeError("failed to connect to database")
