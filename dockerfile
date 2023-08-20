FROM python

# set work directory
WORKDIR /chatgpt_bot

# copy bot files
COPY bot ./bot
COPY chatgpt ./chatgpt
COPY database ./database

# copy scripts and requirements
COPY scripts/start.py ./scripts/start.py
COPY requirements.txt ./requirements.txt

# install requirements and start the bot
RUN pip install -r requirements.txt
ENTRYPOINT [ "scripts/start.py", "--setup-profile", "--log" ]
