#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from utils import print_bold, run_command

from scripts.utils import print_success


def main(clean: bool = False) -> None:
    """Update the bot and start it."""
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(script_dir, ".."))
    current_branch = (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .decode()
        .strip()
    )
    print_bold(f"Current branch: {current_branch}")
    print()

    # update the repo
    update_repo()
    print_success("Updated repository successfully")
    print()

    # setup the bot
    setup_cmd = f"python3 ./scripts/setup.py {'--clean' if clean else ''}"
    if not run_command(setup_cmd):
        print_bold("Error: Bot environment setup failed")
        sys.exit(1)

    # activate virtual environment
    if sys.platform == "win32":
        run_command("& .venv\\Scripts\\Activate.ps1")
    else:
        run_command("source .venv/bin/activate")
    print()

    # start the bot
    bot_cmd = "python3 ./scripts/start.py --log"
    run_command(bot_cmd)


def update_repo():
    changes_stashed = False
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if not run_command('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        changes_stashed = True
        print()

    print_bold("\nUpdating repository...")
    if not run_command("git fetch origin"):
        print_bold("Error: Failed to fetch origin")
        sys.exit(1)
    if not run_command("git pull"):
        print_bold("Error: Failed to pull changes")
        sys.exit(1)
    print()

    if changes_stashed:
        print_bold("\nRestoring changes...")
        if not run_command("git stash pop"):
            print_bold("Error: Failed to restore changes")
            sys.exit(1)
        print()
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
