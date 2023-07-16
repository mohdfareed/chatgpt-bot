#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from utils import print_bold, print_error, print_success, run_command

DEPLOYMENT_BRANCH = "deployment"


def main() -> None:
    """Deploy the bot."""

    current_dir = os.getcwd()
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(os.path.join(script_dir, ".."))
    current_branch = (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .decode()
        .strip()
    )

    if current_branch == DEPLOYMENT_BRANCH:
        print_error("Error: Already on the deployment branch")
        sys.exit(1)
    if not run_command("git status"):
        print_error("Error: Repository is not clean")
        sys.exit(1)

    # stash changes
    changes_stashed = False
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if not run_command('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        changes_stashed = True

    # switch to deployment branch
    if not run_command("git checkout " + DEPLOYMENT_BRANCH):
        print_error("Error: Failed to checkout deployment branch")
        sys.exit(1)
    print()

    # merge current branch into deployment branch
    print_bold(f"Merging {current_branch} into {DEPLOYMENT_BRANCH}...")
    if not run_command("git merge " + current_branch + " --no-commit --no-ff"):
        print_error(
            "Error: Merge failed, resolve conflicts and continue deployment manually"
        )
        sys.exit(1)
    print()

    # update the repo
    print_bold("Committing changes...")
    commit_message = (
        f"Merge branch '{current_branch}' into '{DEPLOYMENT_BRANCH}'"
    )
    if not run_command(f'git commit -m "{commit_message}"'):
        print_error("Error: Failed to commit changes")
        sys.exit(1)
    else:  # push changes
        if not run_command("git push origin " + DEPLOYMENT_BRANCH):
            print_error(
                "Error: Push failed, publish the deployment branch manually"
            )
            sys.exit(1)
    print()

    # switch back to current branch
    if not run_command("git checkout " + current_branch):
        print_error("Error: Failed to switch back to " + current_branch)
        sys.exit(1)
    print()

    # restore stashed changes
    if changes_stashed:
        print_bold("Restoring stashed changes...")
        if not run_command("git stash pop"):
            print_error("Error: Failed to restore stashed changes")
            sys.exit(1)
        print()

    os.chdir(current_dir)
    print_success(f"Successfully deployed to {DEPLOYMENT_BRANCH} branch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy the current branch into the deployment branch"
    )
    args = parser.parse_args()

    main()
