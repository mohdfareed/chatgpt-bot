#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from utils import print_bold, print_success


def main() -> None:
    """Update the bot and start it."""

    # set working directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(script_dir, ".."))

    # stop bot and update repo
    os.system("docker-compose down")
    created_backup = backup()
    update()
    restore() if created_backup else None
    print_success("Repository updated successfully\n")

    # restart bot
    os.system("docker-compose up -d")
    print_success("Bot deployed successfully.")


def backup():
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if os.system('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        return True
    return False


def update():
    print_bold("Updating repository...")
    if os.system("git fetch origin"):
        print_bold("Error: Failed to fetch origin")
        sys.exit(1)
    if os.system("git pull"):
        print_bold("Error: Failed to pull changes")
        sys.exit(1)


def restore():
    print_bold("Restoring changes...")
    if os.system("git stash pop"):
        print_bold("Error: Failed to restore changes")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update and restart the bot.")
    args = parser.parse_args()
    main()
