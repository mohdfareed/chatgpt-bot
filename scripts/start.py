#!/usr/bin/env python3

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

EXCLUDED_MODULES = [
    "httpx",
    "numexpr.utils",
    "openai",
    "telegram.ext.Application",
]  # modules excluded from logging


def setup_bot() -> None:
    """Instantiates and sets up the bot's profile."""

    print("[bold]Setting up bot...[/]")
    # add package directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables and import the bot
    load_dotenv(override=True)

    # setup logging of errors only
    _setup_app(to_file=False, level=logging.ERROR)
    # add package directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)
    # load the bot
    import bot.core as chatgpt_bot

    try:  # run the bot setup
        chatgpt_bot.setup()
    except Exception as e:
        logging.exception(e)
        exit(1)
    exit(0)  # exit when done


def run_app(debug: bool = False, log: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        debug (bool, optional): Whether to log debug messages.
        log (bool, optional): Whether to log to a file. Defaults to console.
    """

    print("[bold]Starting chatgpt_bot...[/]")

    # setup logging
    level = logging.DEBUG if debug else logging.INFO
    _setup_app(to_file=log, level=level)
    # add package directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)
    # load the bot
    import bot.core as chatgpt_bot

    try:  # run the bot
        chatgpt_bot.run()
    except Exception as e:
        logging.exception(e)
        exit(1)


def _setup_app(to_file, level):
    _configure_logging(level)
    root_logger = logging.getLogger()
    _configure_console_logging(root_logger)
    if to_file:  # set up logging to file
        _configure_file_logging(root_logger)


def _configure_logging(level):
    # configure logging
    logging.captureWarnings(True)
    logging.getLogger().level = level
    # don't exclude modules if debugging
    if level == logging.DEBUG:
        return
    # exclude modules from logging
    for module in EXCLUDED_MODULES:
        logging.getLogger(module).setLevel(logging.WARNING)


def _configure_console_logging(logger: logging.Logger):
    format = (
        r"%(message)s [bright_black]- [italic]%(name)s[/italic] "
        r"\[[underline]%(filename)s:%(lineno)d[/underline]]"
    )

    # create console handler
    console_handler = RichHandler(
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        log_time_format="[%Y-%m-%d %H:%M:%S]",
        show_path=False,
    )
    formatter = logging.Formatter(format)

    # setup handler
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def _configure_file_logging(logger: logging.Logger):
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
        "-d", "--debug", action="store_true", help="log debug messages"
    )
    parser.add_argument(
        "-l", "--log", action="store_true", help="log to a file"
    )
    parser.add_argument(
        "--setup", action="store_true", help="setup the bot's profile"
    )

    args = parser.parse_args()
    setup_bot() if args.setup else None
    run_app(args.debug, args.log)
