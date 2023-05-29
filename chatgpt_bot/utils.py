"""Utilities and helper functions."""

from chatgpt.langchain import prompts as _prompts
from telegram import Message as _Message


async def reply_code(message: _Message | None, reply):
    if message:
        await message.reply_html(text=f"<code>{reply}</code>")


def get_prompt(session: str, sessions_prompts: dict[str, str]):
    return sessions_prompts.get(session, _prompts.ASSISTANT_PROMPT)
