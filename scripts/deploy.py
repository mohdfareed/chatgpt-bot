#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys

from utils import print_bold, print_error, print_success

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
    if os.system("git status"):
        print_error("Error: Repository is not clean")
        sys.exit(1)

    # stash changes
    changes_stashed = False
    if subprocess.run("git diff --quiet", shell=True).returncode:
        print_bold("Stashing changes...")
        if os.system('git stash save "Auto stash before update"'):
            print_bold("Error: Failed to stash changes")
            sys.exit(1)
        changes_stashed = True

    # switch to deployment branch
    if os.system("git checkout " + DEPLOYMENT_BRANCH):
        print_error("Error: Failed to checkout deployment branch")
        sys.exit(1)

    # merge current branch into deployment branch
    print_bold(f"Merging {current_branch} into {DEPLOYMENT_BRANCH}...")
    if os.system("git merge " + current_branch + " --no-commit --no-ff"):
        restore(current_branch, changes_stashed)
        print_error(
            "Error: Merge failed, resolve conflicts and continue deployment manually"
        )
        sys.exit(1)

    # update the repo
    print_bold("\nCommitting changes...")
    commit_message = (
        f"Merge branch '{current_branch}' into '{DEPLOYMENT_BRANCH}'"
    )
    if os.system(f'git commit -m "{commit_message}"'):
        restore(current_branch, changes_stashed)
        print_error("Error: Failed to commit changes")
        sys.exit(1)
    else:  # push changes
        print_bold("Pushing changes...")
        if os.system("git push origin " + DEPLOYMENT_BRANCH):
            restore(current_branch, changes_stashed)
            print_error(
                "Error: Push failed, publish the deployment branch manually"
            )
            sys.exit(1)
    print()

    # restore workspace
    restore(current_branch, changes_stashed)
    os.chdir(current_dir)
    print_success(f"\nSuccessfully deployed to {DEPLOYMENT_BRANCH} branch")


def restore(current_branch, changes_stashed):
    # switch back to current branch
    if os.system("git checkout " + current_branch):
        print_error("Error: Failed to switch back to " + current_branch)
        sys.exit(1)
    # restore stashed changes
    if changes_stashed:
        print_bold("Restoring stashed changes...")
        if os.system("git stash pop"):
            print_error("Error: Failed to restore stashed changes")
            sys.exit(1)
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy the current branch into the deployment branch"
    )
    args = parser.parse_args()

    main()
