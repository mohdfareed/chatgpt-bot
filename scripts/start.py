#!/usr/bin/env python3

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

LOGGING_MODULES = ["bot", "chatgpt", "database"]
"""The main logging modules."""


def main(debug=False, log=False, setup_profile=True) -> None:
    """Instantiates and runs the app.
    Args:
        debug (bool): Whether to log debug messages.
        log (bool): Whether to log to a file in addition to the console.
        setup_profile (bool): Whether to setup/update the bot's profile.
    """

    print("[bold]Starting chatgpt_bot...[/]")
    setup_logging(to_file=log, debug=debug)

    # add package directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)  # support for .env file
    # load the bot and the database
    import bot.app as chatgpt_bot
    import database.core as chatgpt_db

    try:  # run the bot and db
        chatgpt_db.initialize()
        chatgpt_bot.run(setup_profile)
    except Exception as e:
        logging.exception(e)
        exit(1)

    print("\n[bold green]chatgpt_bot stopped[/]")


def setup_logging(to_file, debug):
    # configure logging
    logging.captureWarnings(True)
    root_logger = logging.getLogger()
    root_logger.level = logging.WARNING  # default level

    # set up logging level for all modules
    level = logging.DEBUG if debug else logging.INFO
    for module in LOGGING_MODULES:
        logging.getLogger(module).setLevel(level)
    # set up logging level for this module
    (local_logger := logging.getLogger(__name__)).setLevel(level)

    # setup console and file loggers
    configure_console_logging(root_logger, debug)
    if to_file:  # set up logging to file
        configure_file_logging(root_logger)
    local_logger.debug("Debug mode enabled")


def configure_console_logging(logger: logging.Logger, debug: bool):
    format = (
        r"%(message)s [bright_black]- [italic]%(name)s[/italic] "
        r"\[[underline]%(filename)s:%(lineno)d[/underline]]"
    )

    # create console handler
    console_handler = RichHandler(
        markup=True,
        show_path=False,  # use custom path
        log_time_format="[%Y-%m-%d %H:%M:%S]",
        rich_tracebacks=True,
        # show locals only in debug mode
        tracebacks_show_locals=debug,
    )
    formatter = logging.Formatter(format)

    # setup handler
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def configure_file_logging(logger: logging.Logger):
    format = (
        "[%(asctime)s] %(levelname)-8s "
        "%(message)s - %(name)s [%(filename)s:%(lineno)d]"
    )

    # create file handler
    logging_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logging_dir, exist_ok=True)
    filename = f"{datetime.now():%y%m%d_%H%M%S}.log"
    file = os.path.join(logging_dir, filename)
    file_handler = logging.FileHandler(file)
    formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S")

    # setup handler
    logger.addHandler(file_handler)
    file_handler.setFormatter(formatter)
    logger.info(f"Logging to file: {file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start the ChatGPT bot.")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="start in debug mode"
    )
    parser.add_argument(
        "-l", "--log", action="store_true", help="log to a file"
    )
    parser.add_argument(  # default is True
        "-s",
        "--setup-profile",
        action="store_true",
        help="setup/update the bot's profile",
    )

    args = parser.parse_args()
    main(args.debug, args.log, args.setup_profile)
