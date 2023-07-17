#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import venv

from utils import print_bold, print_success

REQ_PATH = os.path.join(os.getcwd(), "requirements.txt")
"""Path to the requirements file."""
VENV_PATH = os.path.join(os.getcwd(), ".venv")
"""Path to the virtual environment."""
NULL = "NUL 2>&1" if sys.platform == "win32" else "/dev/null 2>&1"
"""Path to the null device."""
PYTHON = (
    os.path.join(VENV_PATH, "bin", "python")
    if sys.platform != "win32"
    else os.path.join(VENV_PATH, "Scripts", "python.exe")
)
"""Path to the python executable."""


def main(clean: bool = False, update: bool = False) -> None:
    """Update the bot and start it."""

    # set working directory
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(script_dir, ".."))

    update_repo() if update else None  # update the repo
    setup_env(clean)  # setup the virtual environment

    # start the bot in the virtual environment
    exit(os.system(f"{PYTHON} ./scripts/start.py --log"))


def update_repo():
    # backup changes
    changes_stashed = False
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if os.system('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        changes_stashed = True

    # update repository
    print_bold("Updating repository...")
    if os.system("git fetch origin"):
        print_bold("Error: Failed to fetch origin")
        sys.exit(1)
    if os.system("git pull"):
        print_bold("Error: Failed to pull changes")
        sys.exit(1)

    # restore changes
    if changes_stashed:
        print_bold("Restoring changes...")
        if os.system("git stash pop"):
            print_bold("Error: Failed to restore changes")
            sys.exit(1)
    print_success("Repository updated successfully\n")


def setup_env(clean: bool):
    # create virtual environment
    print_bold("Creating environment...")
    venv.create(
        VENV_PATH,
        clear=clean,
        with_pip=True,
        prompt="chatgpt",
        upgrade_deps=True,
    )
    # install and upgrade dependencies and package manager
    print_bold("Installing dependencies...")
    os.system(f"{PYTHON} -m pip install --upgrade pip > {NULL}")
    os.system(f"{PYTHON} -m pip install -r {REQ_PATH} --upgrade > {NULL}")
    print_success("Environment setup completed successfully\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup and start the bot. Updates the bot if necessary."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="run the bot in a clean environment",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="update the bot",
    )
    args = parser.parse_args()

    main(args.clean, args.update)
