#!/usr/bin/env python3
import os


def main(clean: bool = False) -> None:
    """Setup an environment for the ChatGPT Telegram bot project.

    Args:
        clean (bool, optional): Clean the environment. Defaults to False.
    """

    # set working directory to the directory of this project
    os.chdir(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    # set paths to virtual environment, requirements, and token
    venv = os.path.join(os.getcwd(), ".venv")
    python = os.path.join(venv, "bin", "python3")
    req = os.path.join(os.getcwd(), "requirements.txt")

    if os.path.exists(venv) and clean:
        # remove virtual environment
        os.system(f"rm -rf {venv}")

    # create virtual environment
    os.system(f"python3 -m venv {venv}")
    # update package manager
    os.system(f"{python} -m pip install --upgrade pip")
    # install dependencies, upgrade if already installed
    os.system(f"{python} -m pip install -r {req} --upgrade")

    print("\nsetup complete")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--clean", action="store_true",
                        help="perform a clean setup")
    args = parser.parse_args()
    main(args.clean)
