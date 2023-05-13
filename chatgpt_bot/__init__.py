"""ChatGPT based Telegram bot."""

import logging
import os
from chatgpt.types import GPTMessage, MessageRole

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
"""Telegram bot token."""
WEBHOOK = os.getenv('WEBHOOK', '')
"""Telegram webhook URL."""
WEBHOOK_ADDR = os.getenv('WEBHOOK_ADDR', '')
"""Telegram webhook IP address."""
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '-1'))
"""Telegram webhook port."""
DEV = False
"""Whether the bot is running in development mode."""

if not BOT_TOKEN:
    raise ValueError("environment variables not set")
if not all([WEBHOOK_ADDR, (False if WEBHOOK_PORT < 0 else True), WEBHOOK]):
    DEV = True

logger: logging.Logger = logging.getLogger(__name__)
"""The bot logger."""

bot_prompt = """
Messages are followed by <message id>-<reply id>-<username>.
Reply ID is 0 if the message is not a reply or replying to an unknown message.
You cannot use Markdown. Mention a another user with: @username
Format messages using the following Telegram HTML tags:
<b>bold</b> <i>italic</i> <u>underline</u> <s>strikethrough</s>
<tg-spoiler>spoiler</tg-spoiler> <a href="https://example.com">links</a>
<code>code</code>
<pre><code class="language-python">
pre-formatted fixed-width code block written in the Python programming language
</code></pre>
"""
bot_prompt = GPTMessage(bot_prompt, MessageRole.SYSTEM)
"""The main prompt for the bot. It explains the bot's capabilities."""

prompts: dict[str, str] = {}
"""The list of pre-made prompts mapped by their names."""
DEFAULT_PROMPT: str = 'Default'
"""The default system prompt to use."""


# parse pre-made prompts
_root = os.path.dirname(os.path.realpath(__file__))
prompts[DEFAULT_PROMPT] = ""
with open(os.path.join(_root, 'prompts.txt'), 'r') as _f:
    prompt = DEFAULT_PROMPT
    for _line in _f:
        # prompts are separated by a blank line
        if _line[0] == '#':
            prompt = _line.replace('#', '').strip()
            prompts[prompt] = ""
            continue
        if _line:  # parse the body of the prompt
            prompts[prompt] += _line
            continue

    # remove trailing newlines
    for prompt in prompts:
        prompts[prompt] = prompts[prompt].strip('\n')
