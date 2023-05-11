FROM python

# copy bot files
WORKDIR /usr/src/bot
COPY . .
# install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# start the bot
CMD [  "python", "./scripts/start.py" ]
