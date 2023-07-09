#!/usr/bin/env sh
# publish the current branch to the deployment branch

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
    error "You are already on the $deployment_branch branch."
    exit 1
fi


# switch and merge if
if [ ! $merge_in_progress ]; then

# stash any changes
echo "Stashing changes..."
git stash save "Auto stash before deploying $current_branch" > /dev/null
stash_result=$?
# if stash was successful, set a flag
if [ $stash_result -eq 0 ]; then
    changes_stashed=1
    success "Changes stashed"
fi

# switch to the deployment branch
echo "Switching to the $deployment_branch branch..."
git checkout $deployment_branch > /dev/null
if [ $? -ne 0 ]; then
    error "Failed to switch to the deployment branch."
    exit 1
fi
success "Switched to $deployment_branch branch"

# merge the current branch into deployment
echo "Merging $current_branch into $deployment_branch..."
git merge $current_branch --no-commit --no-ff > /dev/null
if [ $? -ne 0 ]; then
    error "Merge failed. Resolve conflicts and continue the merge manually."
    exit 1
fi
success "Merge successful"

fi # merge is done

# commit the changes to deployment
echo "Committing changes..."
git commit -m "Merge branch '$current_branch' into deployment" > /dev/null
if [ $? -ne 0 ]; then
    error "Commit failed."
    exit 1
fi
success "Changes committed"

# push the changes to the deployment branch
echo "Pushing changes..."
git push origin deployment > /dev/null
if [ $? -ne 0 ]; then
    error "Push failed."
    exit 1
fi
success "Changes pushed"

# switch back to the old branch
echo "Switching back to the $current_branch branch..."
git checkout $current_branch > /dev/null
if [ $? -ne 0 ]; then
    error "Failed to switch back to the original branch."
    exit 1
fi
success "Switched back to $current_branch branch"

# if changes were stashed, pop the stash
if [ $changes_stashed ]; then
    echo "Restoring stashed changes"
    git stash pop  > /dev/null
    if [ $? -ne 0 ]; then
        error "Failed to apply the stash."
        exit 1
    fi
    success "Stash restored"
fi

success "Deployment successful!"

error() {
    RED='\033[0;31m'
    CLEAR='\033[0m'
    echo -e "${RED}Error:${CLEAR} $1"
}

success() {
    GREEN='\033[0;32m'
    CLEAR='\033[0m'
    echo -e "${GREEN}Error:${CLEAR} $1"
}
