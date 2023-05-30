"""Utilities and helper functions."""

from chatgpt.langchain import prompts as _prompts
from telegram import Message as _Message

_sessions_prompts = dict()


async def reply_code(message: _Message | None, reply):
    """Reply to a message with a code block."""

    if message:
        await message.reply_html(text=f"<code>{reply}</code>")


def get_sys_prompt(session: str):
    return _sessions_prompts.get(session, _prompts.ASSISTANT_PROMPT)


def set_sys_prompt(session: str, prompt: str):
    _sessions_prompts[session] = prompt
