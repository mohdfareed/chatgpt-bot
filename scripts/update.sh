#!/usr/bin/env sh
# update the current branch then setup and start the bot

error() {
    BOLDRED='\033[31;1m'
    CLEAR='\033[0m'
    echo "${BOLDRED}Error:${CLEAR} $1"
}

# save the branch names
current_branch=$(git rev-parse --abbrev-ref HEAD)
# set the working directory to the root of the repo
script_dir=$(dirname "$0")
cd "$script_dir/.."

# stash any changes
if ! git diff --quiet; then
    echo "\033[1mStashing changes...\033[0m"
    git stash save "Auto stash before update $current_branch"
    if [ $? -ne 0 ]; then
        error "Failed to stash changes, aborting update"
        exit 1
    fi
    changes_stashed=1  # set a flag to pop the stash later
    echo
fi

# update the current branch
echo "\033[1mUpdating $current_branch...\033[0m"
git fetch origin
if [ $? -ne 0 ]; then
    error "Fetch failed, try again"
    exit 1
else  # pull changes after fetch
    git pull origin $current_branch
    if [ $? -ne 0 ]; then
        error "Merge failed, resolve conflicts and restore changes manually"
        exit 1
    fi
fi

# if changes were stashed, pop the stash
if [ $changes_stashed ]; then
    echo "\n\033[1mRestoring stashed changes\033[0m"
    git stash pop
    if [ $? -ne 0 ]; then
        error "Failed to apply stashed changes"
    fi
fi
echo "\033[32;1mUpdate completed successfully\033[0m"
echo

# setup the virtual environment
./scripts/setup.py --clean
source .venv/bin/activate
echo
# start the bot
./scripts/start.py --setup
./scripts/start.py --log
