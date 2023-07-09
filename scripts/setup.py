#!/usr/bin/env python3

import os
import sys

REQ_PATH = os.path.join(os.getcwd(), "requirements.txt")
"""Path to the requirements file."""


def main(clean: bool = False) -> None:
    """Set up the bot's environment.
    Args:
        clean (bool): Clean the environment.
    """

    print("\u001b[01mSetting up environment...\u001b[0m")
    # set working directory and virtual environment path
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    venv = os.path.join(os.getcwd(), ".venv")

    # set os specific commands
    if sys.platform == "win32":
        python = os.path.join(venv, "Scripts", "python.exe")
        force_remove = "rmdir /s /q"
        null = "NUL 2>&1"
    else:
        python = os.path.join(venv, "bin", "python")
        force_remove = "rm -rf"
        null = "/dev/null 2>&1"

    # remove existing virtual environment if requested
    if os.path.exists(venv) and clean:
        print("Cleaning existing environment...")
        os.system(f"{force_remove} {venv}")

    # create virtual environment
    print("Creating environment...")
    os.system(f"python3 -m venv {venv}")
    # install and upgrade dependencies and package manager
    print("Installing dependencies...")
    os.system(f"{python} -m pip install --upgrade pip > {null}")
    os.system(f"{python} -m pip install -r {REQ_PATH} --upgrade > {null}")
    print("\u001b[32;1mEnvironment setup complete\u001b[0m")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup the ChatGPT bot environment."
    )
    parser.add_argument(
        "-c", "--clean", action="store_true", help="perform a clean setup"
    )

    args = parser.parse_args()
    main(args.clean)
