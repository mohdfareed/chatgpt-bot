FROM python

# set work directory
WORKDIR /chatgpt_bot
# copy bot files
COPY bot ./bot
COPY chatgpt ./chatgpt
COPY database ./database
# copy scripts
COPY scripts ./scripts
# copy requirements
COPY requirements.txt ./requirements.txt
COPY .env ./.env

# start the bot
ENTRYPOINT [ "scripts/run.sh" ]
