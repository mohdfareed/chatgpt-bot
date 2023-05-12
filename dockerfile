FROM python

# copy bot files
WORKDIR /usr/src/bot
COPY . .
# install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt
# start the bot
CMD [ "python", "./scripts/start.py" ]
