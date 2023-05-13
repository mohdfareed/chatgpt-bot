# ChatGPT Telegram Bot

ChatGPT interface using Telegram's bot API. The bot is currently hosted at
[@MohdFareed_ChatGPT_Bot](https://t.me/MohdFareed_ChatGPT_Bot).

## Setup

### Requirements

The following environment variables are required:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`: Postgres database URL

### Installation

Download the repository and run the setup script:

```sh
git clone https://github.com/mohdfareed/chatgpt-telegram.git
cd path/to/chatgpt-telegram
./scripts/setup.py [--clean]
```

- The `--clean` flag will remove the existing virtual environment.

Fill in the provided example environment file and renamed it to `.env`.

### For local development

If developing `chatgpt` with the bot locally, install local `chatgpt` using:

```sh
cd path/to/chatgpt-telegram
source .venv/bin/activate
pip install -e /path/to/chatgpt
```

Run Postgres database docker container at `localhost:5432` if not already
running using:

```sh
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD={db_password} \
--name chatgpt-db postgres
```

Set the following environment variables in `.env`:

```sh
OPENAI_API_KEY='sk-{...}'
TELEGRAM_BOT_TOKEN='{...}:{...}'  # use separate token for development
DATABASE_URL="postgresql://postgres:{db_password}@localhost/postgres"
PYTHONPATH='/path/to/chatgpt'
```

Run the bot using the container:

```sh
cd path/to/chatgpt-telegram
docker build -t chatgpt-bot .
docker run --rm --env-file .env chatgpt-bot
```

## Usage

Start the bot using the virtual environment:

```sh
cd path/to/chatgpt-telegram
source .venv/bin/activate
./scripts/start.py [--debug] [--log] [--clean]
```

- `--debug`: flag will log debug messages. Defaults to logging info messages.
- `--log`: flag will log messages to a file. Defaults to logging to stdout.
- `--clean`: flag will remove the existing database docker container and will
    not restore the database from a backup.

### Deployment to [Fly.io](https://fly.io)

The bot is deployed to Fly.io using GitHub Actions. To deploy the bot to Fly.io
manually, install
[Fly CLI](https://fly.io/docs/getting-started/installing-flyctl/), configure
`fly.toml` file, and run:

```sh
cd path/to/chatgpt-telegram
fly auth signup # `fly auth login` if already signed up
fly launch  # `fly deploy` if already launched
```

Deployment is triggered on push to the `deployment` branch. The following repo
secrets is required: `FLY_API_TOKEN`

The app on Fly.io needs to have the following environment variables set:

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `DATABASE_URL`

Monitor the logs using:

```sh
fly logs -a {app name}
```

## Database

The database is a docker container running a PostgreSQL database. It acts as a
persistent storage for the bot. The database contains inforamtion that builds
the context of the conversation. The following is the database schema:

```mermaid
erDiagram
    Chat ||--o{ Message : contains
    Topic |o--o{ Message : contains
    Chat ||--o{ Topic : has
    User |o--o{ Message : sends
    Message ||--o{ Message : replies_to
    Chat {
        int id
    }
    Topic {
        int id
        int chat_id
    }
    User {
        int id
    }
    Message {
        int id
        int chat_id
    }
```

## Pre-Made System Prompts

The bot comes with a few pre-made prompts that can be presented to the user.
The prompts are stored in `chatgpt_bot/prompts.txt`. Text proceeding the first
title is considered the default prompt for the bot. The default's prompt's
name is `Default`, unless changed in the source code. Each prompt starts with
a title and is followed by the prompt itself. The file has the following format:

```markdown
# Default (optional)
The default prompt's content.

# Title
The prompt's content.

# Another Title
Another prompt's content.
```

The prompts' content is trimmed of leading and trailing whitespace, allowing
for better organization of the prompts in the file.
