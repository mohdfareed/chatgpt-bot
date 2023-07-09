#!/usr/bin/env sh
# publish the current branch to the deployment branch

error() {
    BOLDRED='\033[31;1m'
    CLEAR='\033[0m'
    echo "${BOLDRED}Error:${CLEAR} $1"
}

# set the working directory to the root of the repo
current_dir=$(pwd)
script_dir=$(dirname "$0")
cd "$script_dir/.."
# save the branch names
deployment_branch="deployment"
current_branch=$(git rev-parse --abbrev-ref HEAD)
# check if a merge is in progress
if git rev-parse --verify MERGE_HEAD > /dev/null 2>&1; then
  merge_in_progress=1
fi

# check if the current branch is the deployment branch and no merge in progress
if [ "$current_branch" = "$deployment_branch" ] && [ ! $merge_in_progress ]; then
    error "You are already on the $deployment_branch branch"
    exit 1
fi

# switch and merge if
if [ ! $merge_in_progress ]; then

# stash any changes
if ! git diff --quiet; then
    echo "\033[1mStashing changes...\033[0m"
    git stash save "Auto stash before deploying $current_branch"
    if [ $? -ne 0 ]; then
        error "Failed to stash changes, aborting deployment"
        exit 1
    fi
    changes_stashed=1  # set a flag to pop the stash later
    echo
fi

# switch to the deployment branch
git checkout $deployment_branch
if [ $? -ne 0 ]; then
    error "Failed to switch to the deployment branch"
    exit 1
fi
echo

# merge the current branch into deployment
echo "\033[1mMerging $current_branch into $deployment_branch...\033[0m"
git merge $current_branch --no-commit --no-ff
if [ $? -ne 0 ]; then
    error "Merge failed, resolve conflicts and continue deployment manually"
    exit 1
fi
echo

fi # merge is done

# commit the changes to deployment
echo "\033[1mCommitting changes...\033[0m"
git commit -m "Merge branch '$current_branch' into deployment"
if [ $? -ne 0 ]; then
    error "Committing failed"
# push the changes to the deployment branch
else
    echo "\n\033[1mPushing changes...\033[0m"
    git push origin deployment
    if [ $? -ne 0 ]; then
        error "Push failed, publish the deployment branch manually"
    fi
fi

# switch back to the old branch
git checkout $current_branch
if [ $? -ne 0 ]; then
    error "Failed to switch back to the original branch"
    exit 1
fi
echo

# if changes were stashed, pop the stash
if [ $changes_stashed ]; then
    echo "\033[1mRestoring stashed changes\033[0m"
    git stash pop
    if [ $? -ne 0 ]; then
        error "Failed to apply stashed changes"
        exit 1
    fi
    echo
fi

cd "$current_dir"
echo "\033[32;1mDeployment successfully done\033[0m"
