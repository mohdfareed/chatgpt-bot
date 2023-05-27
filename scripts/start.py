#!/usr/bin/env python3


import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler


def main(debug: bool = False, log: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        debug (bool, optional): Whether to log debug messages.
        log (bool, optional): Whether to log to a file. Defaults to console.
    """

    print("[bold green]Starting chatgpt_bot...[/]")
    # add bot directory to the path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)
    # setup logging
    _setup(to_file=log, debug=debug)

    try:  # start telegram bot
        import database.core as db
        from chatgpt_bot import bot

        db.start()  # start database
        bot.run()  # run bot
    except Exception as e:
        logging.error(e)
        exit(1)


def _setup(to_file: bool = False, debug: bool = False):
    # configure logging
    logging.captureWarnings(True)
    level = logging.DEBUG if debug else logging.INFO

    # create console logger and set format
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    format = "%(message)s [italic black](%(name)s)[/]"
    formatter = logging.Formatter(format)

    # create handler
    console_handler = RichHandler(
        markup=True,
        rich_tracebacks=True,
        log_time_format="[%Y-%m-%d %H:%M:%S]",
    )
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if to_file:  # set up logging to file
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        file = os.path.join(logs_dir, f"{datetime.now():%y%m%d_%H%M%S}.log")

        # set file format
        format = (
            "[%(asctime)s] %(levelname)-8s "
            "%(message)s (%(name)s) - %(filename)s:%(lineno)d"
        )
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S")

        # create file handler
        file_handler = logging.FileHandler(file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"logging to file: {file}")


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
    main(args.debug, args.log)
