FROM python

# copy bot files
WORKDIR /usr/src/bot
COPY chatgpt_bot ./chatgpt_bot
COPY database ./database
# install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt
# start the bot
COPY scripts ./scripts
CMD [ "python", "scripts/start.py" ]
