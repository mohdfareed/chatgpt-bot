"""ChatGPT based Telegram bot."""

import logging
import os
from email.policy import default

from chatgpt.messages import Message as GPTMessage
from dotenv import load_dotenv

_root = os.path.dirname(os.path.realpath(__file__))
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
"""Telegram bot token."""
OPENAI_KEY = os.getenv('OPENAI_KEY', '')
"""OpenAI API key."""

logger: logging.Logger = logging.getLogger(__name__)
"""The bot logger."""

bot_prompt = """
Messages in the chat history are embedded with the following:
<MessageID>-<InReplyToID>-<Username>
The `<InReplyToID>` is the ID of the message to which the message is replying.
It is `0` if the message is not a reply or replying to an unknown message.
Mention a another user with: @username
Format messages using the following Telegram HTML tags:
<b>bold</b> <i>italic</i> <u>underline</u> <s>strikethrough</s>
<tg-spoiler>spoiler</tg-spoiler> <a href="https://example.com">links</a>
<code>code</code>
<pre><code class="language-python">
pre-formatted fixed-width code block written in the Python programming language
</code></pre>
"""
bot_prompt = GPTMessage(GPTMessage.Role.SYSTEM, bot_prompt)
"""The main prompt for the bot. It explains the bot's capabilities."""

prompts: dict[str, str] = {}
"""The list of pre-made prompts mapped by their names."""
DEFAULT_PROMPT: str = 'Default'
"""The default system prompt to use."""

if not BOT_TOKEN:
    raise ValueError("'BOT_TOKEN' environment variable not set")

# parse pre-made prompts
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
