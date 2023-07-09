#!/usr/bin/env sh
# set up a tmux session with a server and client window
session_name="chatgpt"

# stop pre existing sessions
tmux kill-session -t $session_name
# start a new tmux session with a server window
tmux new-session -d -s $session_name
tmux new-window -t $session_name:0 -n 'server'

# create new windows for clients
tmux new-window -t $session_name:1 -n 'client_1'
tmux new-window -t $session_name:2 -n 'client_2'
tmux new-window -t $session_name:3 -n 'client_3'

# attach to the session and setup the server
tmux attach-session -t $session_name
tmux send-keys -t $session_name:0 './scripts/update.sh' C-m
