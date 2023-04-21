# ChatGPT Telegram Bot

ChatGPT interface using Telegram's bot API. The bot is currently hosted at [@MohdFareed_ChatGPT_Bot](https://t.me/MohdFareed_ChatGPT_Bot).

## Installation

Download the repository and run the setup script:

```sh
git clone https://github.com/mohdfareed/chatgpt-telegram.git
cd chatgpt-telegram
./scripts/setup.py
```

## Setup

Add the following to the `config/` directory:

- `TOKEN`: Telegram bot token (obtained from [@BotFather](https://t.me/BotFather))

### For local development

The setup script uses a virtual environment. It also loads the `.env` file from the process environment with the name `TELEGRAM_BOT_TOKEN`. You can set this variable in your shell to avoid having to add the token to the `config/` directory.

## Usage

Run the bot:

```sh
./run.py
```
