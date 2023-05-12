#!/usr/bin/env python3
import logging
import os
import sys
from datetime import datetime


def main(debug: bool = False, log: bool = False, clean: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        debug (bool, optional): Whether to log debug messages.
        log (bool, optional): Whether to log to a file. Defaults to console.
        clean (bool, optional): Whether to start a clean database.
    """
    print(f"\033[0;32m{'starting chatgpt bot...'}\033[0m")
    _setup()

    if log:  # set up logging to file
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        file = os.path.join(logs_dir, f'{datetime.now():%y%m%d_%H%M%S}.log')
    else:  # log to console
        file = None

    format = '[%(levelname)s] %(message)s - %(name)s (%(filename)s:%(lineno)d)'
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(filename=file, level=level, format=format)
    logging.captureWarnings(True)

    import database.core as db
    from chatgpt_bot import bot
    try:  # start the database and run the bot
        db.start(clean)
        bot.run()
    except Exception as e:
        print(f"\033[0;31m{'error:'}\033[0m {e}")
        exit(1)
    finally:
        db.stop()


def _setup():
    """Sets up the environment for the bot."""
    from dotenv import load_dotenv

    # set working directory to the directory of this project
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    # add the bot directory to the path
    sys.path.append(os.getcwd())
    # load environment variables
    load_dotenv(override=True)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser('chatgpt_bot')
    parser.add_argument("-d", "--debug", action="store_true",
                        help="log debug messages")
    parser.add_argument("-l", "--log", action="store_true",
                        help="log to a file")
    parser.add_argument("-c", "--clean", action="store_true",
                        help="start a clean database")
    args = parser.parse_args()
    main(args.debug, args.log, args.clean)
