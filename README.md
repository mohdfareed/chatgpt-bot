# ChatGPT Telegram Bot

ChatGPT interface using Telegram's bot API. The bot is currently hosted at [@MohdFareed_ChatGPT_Bot](https://t.me/MohdFareed_ChatGPT_Bot). The bot relies on a `telethon` Telegram client to sync messages with the Telegram server.

## Installation

Download the repository and run the setup script:

```sh
git clone https://github.com/mohdfareed/chatgpt-telegram.git
cd chatgpt-telegram
./scripts/setup.py
```

## Setup

Add the following to the `config/` directory:

- Passport private key as `passport.key`
- The following environment variables to `.env`:
  - `BOT_TOKEN`: Telegram bot token (obtained from [@BotFather](https://t.me/BotFather))
  - `APPID`: Telegram application API ID (obtained from [my.telegram.org](https://my.telegram.org))
  - `APPID_HASH`: Telegram application API hash (obtained from [my.telegram.org](https://my.telegram.org))

### For local development

The setup script uses a virtual environment. It also loads the `.env` file from the process environment with the following names:

- 'TELEGRAM_BOT_TOKEN'
- 'TELEGRAM_APP_ID'
- 'TELEGRAM_APP_ID_HASH'

## Usage

Run the bot:

```sh
./chatgpt.py
```
