FROM python

# copy bot files
WORKDIR /usr/src/app
COPY bot ./bot
COPY chatgpt ./chatgpt
COPY database ./database
COPY scripts ./scripts

# start the bot
CMD [ "scripts/update.sh" ]
