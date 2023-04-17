#!/usr/bin/env python3
import os

REQUIREMENTS = "requirements"
"""Path to the requirements files directory."""


def main(dev: bool = False) -> None:
    """Setup an environment for the ChatGPT Telegram bot project.

    Args:
        dev (bool, optional): Setup development environment. Defaults to False.
    """

    # set working directory to the directory of this project
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    # set paths of virtual environment and requirements directory
    venv = os.path.join(os.getcwd(), ".venv")
    python = os.path.join(venv, "bin", "python3")
    req_dir = os.path.join(os.getcwd(), REQUIREMENTS)

    # create virtual environment
    os.system(f"python3 -m venv {venv}")
    # update package manager
    os.system(f"{python} -m pip install --upgrade pip")
    # install dependencies
    req = os.path.join(req_dir, "development.txt" if dev else "common.txt")
    os.system(f"{python} -m pip install -r {req}")


if __name__ == "__main__":
    import argparse

    # parse arguments
    parser = argparse.ArgumentParser("setup")
    parser.add_argument("-d", "--dev", action="store_true",
                        help="setup a development environment"
                        )
    args = parser.parse_args()
    main(args.dev)
