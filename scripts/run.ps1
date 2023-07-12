# update the current branch then setup and start the bot

param(
    [switch]$clean # clean the virtual environment before setup
)

# write a formatted error message
function Write-Error {
    param([String]$Message)
    Write-Host "`e[31;1mError:`e[0m $Message"
}

# save the branch names
$current_branch = git rev-parse --abbrev-ref HEAD
# set the working directory to the root of the repo
$script_dir = Split-Path $MyInvocation.MyCommand.Path -Parent
Set-Location "$script_dir/.."

# stash any changes if there are any
git stash save "Auto stash before update $current_branch"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to stash changes, aborting update"
    exit 1
}
Write-Host

# update the current branch
git fetch origin
if ($LASTEXITCODE -ne 0) {
    Write-Error "Fetch failed, try again"
    exit 1
} else  { # pull changes after fetch
    git pull origin $current_branch
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Merge failed, resolve conflicts and restore changes manually"
        exit 1
    }
}

# if changes were stashed, pop the stash
git stash pop
# TODO: check if stash pop failed
Write-Host "`e[32;1mUpdate completed successfully`e[0m`n"

# setup the virtual environment
python .\scripts\setup.py --clean:$clean
& .venv\Scripts\Activate.ps1
Write-Host
# start the bot
python .\scripts\start.py --log
