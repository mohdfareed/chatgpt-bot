"""Utilities and helper functions."""

import telegram

import bot.models
import chatgpt.core
import chatgpt.memory
import chatgpt.model


async def reply_code(message: telegram.Message | None, reply):
    """Reply to a message with a code block."""
    if message:
        await message.reply_html(text=f"<code>{reply}</code>")


async def load_prompt(message: bot.models.TextMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return chat_model.prompt


async def save_prompt(message: bot.models.TextMessage, prompt: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.prompt = chatgpt.core.SystemMessage(prompt)
    await chat_history.set_model(chat_model)


async def count_usage(
    message: bot.models.TextMessage, results: chatgpt.core.ModelMessage
):
    total_usage = results.prompt_tokens + results.reply_tokens

    # count towards user
    db_user = await bot.models.TelegramMetrics(
        model_id=str(message.user.id)
    ).load()
    db_user.usage += total_usage
    db_user.usage_cost += results.cost
    await db_user.save()

    # count towards chat
    db_chat = await bot.models.TelegramMetrics(model_id=message.chat_id).load()
    db_chat.usage += total_usage
    db_chat.usage_cost += results.cost
    await db_chat.save()
