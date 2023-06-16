"""Utilities and helper functions."""

import telegram

import bot.models
import chatgpt.core
import chatgpt.models
import database


async def reply_code(message: telegram.Message | None, reply):
    """Reply to a message with a code block."""

    if message:
        await message.reply_html(text=f"<code>{reply}</code>")


def load_prompt(id: int, topic_id: int | None):
    db_chat = database.models.Chat(id, topic_id).load()
    db_model = database.models.ChatModel(db_chat.session_id).load()
    model = chatgpt.models.ChatModel().from_json(db_model.parameters)
    return model.prompt


def save_prompt(id: int, topic_id: int | None, prompt: str):
    db_chat = database.models.Chat(id, topic_id).load()
    db_model = database.models.ChatModel(db_chat.session_id).load()
    model = chatgpt.models.ChatModel().from_json(db_model.parameters)
    model.prompt = prompt
    db_model.parameters = model.to_json()
    db_model.save()


def count_usage(
    message: bot.models.TextMessage, results: chatgpt.models.ModelReply
):
    total_usage = results.prompt_tokens + results.reply_tokens

    # count towards user
    db_user = database.models.User(message.user.id).load()
    db_user.token_usage += total_usage
    db_user.usage += results.cost
    db_user.save()

    # count towards chat
    db_chat = database.models.Chat(message.chat.id, message.topic_id).load()
    db_chat.token_usage += total_usage
    db_chat.usage += results.cost
    db_chat.save()


def parse_update(update):
    if not (update_message := update.effective_message):
        return
    message = bot.models.TextMessage.from_telegram_message(update_message)
