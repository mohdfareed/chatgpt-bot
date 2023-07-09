#!/usr/bin/env sh
# publish the current branch to the deployment branch

error() {
    RED='\033[0;31m'
    CLEAR='\033[0m'
    echo "${RED}Error:${CLEAR} $1"
}

# set the working directory to the root of the repo
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
    echo "Stashing changes..."
    git stash save "Auto stash before deploying $current_branch" > /dev/null
    # if stash was successful, set a flag
    if [ $stash_result -eq 0 ]; then
        changes_stashed=1
    fi
fi

# switch to the deployment branch
echo "Switching to the $deployment_branch branch..."
git checkout $deployment_branch > /dev/null
if [ $? -ne 0 ]; then
    error "Failed to switch to the deployment branch"
    exit 1
fi

# merge the current branch into deployment
echo "Merging $current_branch into $deployment_branch..."
git merge $current_branch --no-commit --no-ff > /dev/null
if [ $? -ne 0 ]; then
    error "Merge failed. Resolve conflicts and continue deployment manually"
    exit 1
fi

fi # merge is done

# commit the changes to deployment
echo "Committing changes..."
git commit -m "Merge branch '$current_branch' into deployment" > /dev/null
if [ $? -ne 0 ]; then
    error "Commit failed, try again"

# push the changes to the deployment branch
else
    echo "Pushing changes..."
    git push origin deployment > /dev/null
    if [ $? -ne 0 ]; then
        error "Push failed, publish the deployment branch manually"
    fi
fi

# switch back to the old branch
echo "Switching back to the $current_branch branch..."
git checkout $current_branch > /dev/null
if [ $? -ne 0 ]; then
    error "Failed to switch back to the original branch"
    exit 1
fi

# if changes were stashed, pop the stash
if [ $changes_stashed ]; then
    echo "Restoring stashed changes"
    git stash pop  > /dev/null
    if [ $? -ne 0 ]; then
        error "Failed to apply the stash"
        exit 1
    fi
fi

echo "\033[0;32mDeployment was successfully done\033[0m"
