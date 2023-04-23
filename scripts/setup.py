#!/usr/bin/env python3
import os


def main() -> None:
    """Setup an environment for the ChatGPT Telegram bot project.

    Args:
        dev (bool, optional): Setup development environment. Defaults to False.
    """

    # set working directory to the directory of this project
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    # set paths to virtual environment, requirements, and token
    venv = os.path.join(os.getcwd(), ".venv")
    python = os.path.join(venv, "bin", "python3")
    req = os.path.join(os.getcwd(), "requirements.txt")

    # create virtual environment
    os.system(f"python3 -m venv {venv}")
    # update package manager
    os.system(f"{python} -m pip install --upgrade pip")
    # install dependencies
    os.system(f"{python} -m pip install -r {req}")

    print("\nsetup complete")


if __name__ == "__main__":
    main()
