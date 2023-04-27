#!/usr/bin/env python3
import logging
import os
import sys
from datetime import datetime

# set working directory to the directory of this project
os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
# add the project directory to the path
sys.path.append(os.getcwd())


def main(restore: bool = False, log: bool = False) -> None:
    """Instantiates and runs the app. This function sets up logging and
    checks the validity of the configured Telegram bot token.

    Args:
        restore (bool, optional): Whether to load the database from backup.
        log (bool, optional): Whether to log to a file. Defaults to console.
    """

    if log:  # set up logging to file
        logs_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        file = os.path.join(logs_dir, f'{datetime.now():%y%m%d_%H%M%S}.log')
    else:  # log to console
        file = None
    # format = ('%(asctime)s[%(levelname)s] %(name)s - ' +
    #             '%(message)s (%(filename)s:%(lineno)d)')
    format = '[%(levelname)s] %(message)s - %(name)s (%(filename)s:%(lineno)d)'
    logging.basicConfig(
        filename=file,
        level=logging.INFO,
        format=format
    )

    try:  # initialize the database and start the bot
        import database.core as db
        from chatgpt_bot import bot

        # start the database
        db.start()
        db.restore() if restore else None

        # run the bot
        bot.run()

        # stop the database
        db.backup()
        db.stop()
    except Exception as e:
        print(f"\033[0;31m{'error:'}\033[0m {e}")
        exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--restore", action="store_true",
                        help="load database from backup")
    parser.add_argument("-l", "--log", action="store_true",
                        help="log to a file")
    args = parser.parse_args()
    main(args.restore, args.log)
