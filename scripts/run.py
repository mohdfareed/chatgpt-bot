#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from utils import print_bold, print_success


def main(clean: bool = False) -> None:
    """Update the bot and start it."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(script_dir, ".."))
    current_branch = (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .decode()
        .strip()
    )
    print_bold(f"Deployed branch: {current_branch}\n")

    # update the repo
    update_repo()
    print_success("Updated repository successfully\n")

    # setup the bot
    if os.system(f"python3 ./scripts/setup.py {'--clean' if clean else ''}"):
        print_bold("Error: Bot environment setup failed")
        sys.exit(1)

    # activate virtual environment
    if sys.platform == "win32":
        env_cmd = "& .venv\\Scripts\\Activate.ps1 &&"
    else:
        env_cmd = "source .venv/bin/activate &&"
    print()

    # start the bot
    exit(os.system(f"{env_cmd} python3 ./scripts/start.py --log"))


def update_repo():
    changes_stashed = False
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if os.system('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        changes_stashed = True

    print_bold("Updating repository...")
    if os.system("git fetch origin"):
        print_bold("Error: Failed to fetch origin")
        sys.exit(1)
    if os.system("git pull"):
        print_bold("Error: Failed to pull changes")
        sys.exit(1)

    if changes_stashed:
        print_bold("Restoring changes...")
        if os.system("git stash pop"):
            print_bold("Error: Failed to restore changes")
            sys.exit(1)
    return changes_stashed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update the current branch then setup and start the bot."
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="run the bot in a clean environment",
    )
    args = parser.parse_args()

    main(args.clean)
