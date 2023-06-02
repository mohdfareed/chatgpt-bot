FROM python

# copy bot files
WORKDIR /usr/src/bot
COPY bot ./bot
COPY chatgpt ./chatgpt
COPY database ./database
# install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt
# start the bot
COPY scripts ./scripts
CMD [ "python", "scripts/start.py" ]
