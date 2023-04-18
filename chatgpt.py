#!/usr/bin/env python3
import logging
import os
from datetime import datetime

import requests
from rich import print

from chatgpt import bot
from config import TOKEN

LOGS = os.path.join(os.getcwd(), "logs")
"""Path to the logs directory."""


def main(log: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        log (bool, optional): Whether to log to a file. Defaults to False.
    """

    # check if the bot token is valid
    response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe')
    # if the response status code is successful
    if response.status_code == 401:
        print('[bold red]ERROR:[/] Invalid OpenAI API key.')
        print(f"Set 'OPENAI_API_KEY' environment variable to a valid key.")
        exit(1)

    # setup logging
    if log:
        # create logs directory if it doesn't exist
        os.makedirs(LOGS, exist_ok=True)
        # set up logging to file
        file = os.path.join(LOGS, f'{datetime.now():%y%m%d_%H%M%S}.log')
        logging.basicConfig(
            filename=file,
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)8s] %(name)s - %(message)s',
        )

    # start the bot
    logging.debug("starting bot...")
    bot.run()
    logging.debug("bot has stopped.")


def entry_point() -> None:
    """The entry point for the CLI command."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log", action="store_true",
                        help="log to a file"
                        )
    args = parser.parse_args()
    main(args.log)


if __name__ == "__main__":
    entry_point()
