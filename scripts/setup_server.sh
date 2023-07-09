#!/usr/bin/env sh
# set up a tmux session with a server and client window

# start a new tmux session with a server window
tmux new-session -d -s chatgpt
tmux new-window -t chatgpt:0 -n 'server'

# create a new window for the client
tmux new-window -t chatgpt:1 -n 'client_1'
tmux new-window -t chatgpt:2 -n 'client_2'

# attach to the session and setup the server
tmux attach-session -t chatgpt
tmux send-keys -t chatgpt:0 './scripts/update.sh' C-m
