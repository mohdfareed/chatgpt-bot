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
    return chat_model.prompt or chatgpt.core.SystemMessage("")


async def save_prompt(message: bot.models.TextMessage, prompt: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.prompt = chatgpt.core.SystemMessage(prompt)
    await chat_history.set_model(chat_model)


async def count_usage(
    message: bot.models.TextMessage, results: chatgpt.core.ModelMessage
):
    token_usage = results.prompt_tokens + results.reply_tokens
    usage_cost = results.cost

    user_metrics = await bot.models.TelegramMetrics(
        entity_id=str(message.user.id)
    ).load()
    user_metrics.usage += token_usage
    user_metrics.usage_cost += usage_cost
    await user_metrics.save()

    chat_metrics = await bot.models.TelegramMetrics(
        entity_id=str(message.chat.id)
    ).load()
    chat_metrics.usage += token_usage
    chat_metrics.usage_cost += usage_cost
    await chat_metrics.save()
