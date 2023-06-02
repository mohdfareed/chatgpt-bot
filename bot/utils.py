"""Utilities and helper functions."""

import telegram

import bot.models
import database
from chatgpt.langchain.agent import GenerationResults


async def reply_code(message: telegram.Message | None, reply):
    """Reply to a message with a code block."""

    if message:
        await message.reply_html(text=f"<code>{reply}</code>")


def load_prompt(id: int, topic_id: int | None):
    chat = database.Chat(id, topic_id).load()
    return chat.model.prompt


def save_prompt(id: int, topic_id: int | None, prompt: str):
    chat = database.Chat(id, topic_id).load()
    chat.model.prompt = prompt
    chat.save()


def count_usage(message: bot.models.TextMessage, results: GenerationResults):
    total_usage = results.prompt_tokens + results.generated_tokens

    # count towards user
    db_user = database.User(message.user.id)
    db_user.token_usage += total_usage
    db_user.usage += results.cost
    db_user.save()

    # count towards chat
    db_chat = database.Chat(message.chat.id, message.topic_id)
    db_chat.token_usage += total_usage
    db_chat.usage += results.cost
    db_chat.save()
