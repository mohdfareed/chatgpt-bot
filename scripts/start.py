#!/usr/bin/env python3

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

DEFAULT_LOGGING_LEVEL = logging.INFO
"""Default logging level."""
LOGGING_DIR = os.path.join(os.getcwd(), "logs")
"""Path to the logging directory."""


def main(debug: bool = False, log: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        debug (bool, optional): Whether to log debug messages.
        log (bool, optional): Whether to log to a file. Defaults to console.
    """

    print("[bold green]Starting chatgpt_bot...[/]")

    # setup logging
    level = logging.DEBUG if debug else logging.INFO
    _configure_logging(level=level)
    _setup(to_file=log)
    # add bot directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)

    try:
        # import database and bot
        import database.core as database
        from chatgpt_bot import bot as telegram_bot

        # start database and bot
        database.start()
        telegram_bot.run()
    except Exception as e:
        logging.exception(e)
        exit(1)


def _setup(to_file: bool = False):
    root_logger = logging.getLogger()
    format = (
        r"%(message)s [bright_black]- [italic]%(name)s[/italic] "
        r"\[[underline]%(filename)s:%(lineno)d[/underline]]"
    )

    # create console handler
    console_handler = RichHandler(
        markup=True,
        rich_tracebacks=True,
        log_time_format="[%Y-%m-%d %H:%M:%S]",
        show_path=False,
    )
    formatter = logging.Formatter(format)

    # setup handler
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if to_file:  # set up logging to file
        os.makedirs(LOGGING_DIR, exist_ok=True)
        filename = f"{datetime.now():%y%m%d_%H%M%S}.log"
        file = os.path.join(LOGGING_DIR, filename)
        file_handler = logging.FileHandler(file)

        # setup formatting
        format = (
            "[%(asctime)s] %(levelname)-8s "
            "%(message)s - %(name)s [%(filename)s:%(lineno)d]"
        )
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S")

        # setup handler
        root_logger.addHandler(file_handler)
        file_handler.setFormatter(formatter)
        root_logger.info(f"Logging to file: {file}")


def _configure_logging(level: int = DEFAULT_LOGGING_LEVEL):
    # configure logging
    logging.captureWarnings(True)
    logging.getLogger().level = level
    # don't exclude modules if debugging
    if level == logging.DEBUG:
        return

    # exclude modules from logging
    excluded_modules = [
        "httpx",
        "numexpr.utils",
        "openai",
    ]
    for module in excluded_modules:
        logging.getLogger(module).setLevel(logging.WARNING)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("chatgpt_bot")
    parser.add_argument(
        "-d", "--debug", action="store_true", help="log debug messages"
    )
    parser.add_argument(
        "-l", "--log", action="store_true", help="log to a file"
    )

    args = parser.parse_args()
    main(args.debug, args.log)
