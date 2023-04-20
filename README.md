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
  - `TOKEN`: Telegram bot token
  - `APPID`: Telegram application API ID
  - `APPID_HASH`: Telegram application API hash

## Usage

Run the bot:

```sh
./chatgpt.py
```
