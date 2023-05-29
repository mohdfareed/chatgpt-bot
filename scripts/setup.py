#!/usr/bin/env python3


import os
import sys


def main(clean: bool = False) -> None:
    """Setup an environment for the ChatGPT Telegram bot project.

    Args:
        clean (bool, optional): Clean the environment. No-op for development.
    """

    # set working directory to the directory of this project
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    # set paths to virtual environment and requirements
    venv = os.path.join(os.getcwd(), ".venv")
    req = os.path.join(os.getcwd(), "requirements.txt")

    # set path to python executable depending on OS
    if sys.platform == "win32":
        python = os.path.join(venv, "Scripts", "python.exe")
    else:
        python = os.path.join(venv, "bin", "python")

    # remove virtual environment if it exists and clean is set
    if os.path.exists(venv) and clean:
        print("Cleaning environment...")
        if sys.platform == "win32":
            os.system(f"rmdir /s /q {venv}")
        else:
            os.system(f"rm -rf {venv}")

    # create virtual environment
    print("Setting up environment...")
    os.system(f"python3 -m venv {venv}")
    # update package manager
    print("Updating pip...")
    os.system(f"{python} -m pip install --upgrade pip")
    # install dependencies, upgrade if already installed
    print("Installing dependencies...")
    os.system(f"{python} -m pip install -r {req} --upgrade")

    print("\nSetup complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--clean", action="store_true", help="perform a clean setup"
    )
    args = parser.parse_args()
    main(args.clean)
