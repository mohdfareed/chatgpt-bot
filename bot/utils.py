"""Utilities and helper functions."""

import chatgpt.core
import chatgpt.memory
import chatgpt.messages
import chatgpt.model
import chatgpt.tools
from bot import chat_handler, core, logger, metrics, telegram_utils


async def reply_to_user(message: core.TextMessage, reply=False):
    """Reply to a user with a generated model reply."""
    # create handlers
    handler = chat_handler.ModelMessageHandler(message, reply=reply)
    metrics_handler = metrics.ModelMetricsHandler(message)
    # initialize model's memory
    memory = await chatgpt.memory.ChatMemory.initialize(
        message.chat_id,
        summarization_handlers=[metrics_handler],
    )
    # clean memory
    await clean_memory(memory, message.chat.id)
    # setup the chat model
    model = chatgpt.model.ChatModel(
        memory=memory,
        handlers=[handler, metrics_handler],
    )

    return await model.run(message.to_chat_message())


async def add_message(message: core.TextMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.add_message(message.to_chat_message())


async def get_message(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    return await chat_history.get_message(str(message.id))


async def delete_message(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.delete_message(str(message.id))


async def delete_history(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    messages = await chat_history.messages

    deleted_messages: list[str] = []  # IDs of deleted messages
    for model_message in messages:
        if model_message.pinned:
            continue  # prevent deleting pinned messages

        await chat_history.delete_message(model_message.id)
        deleted_messages.append(model_message.id)
    return deleted_messages


async def pin_message(message: core.TelegramMessage) -> bool:
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    history_message = await chat_history.get_message(str(message.id))
    if not history_message:
        return False

    history_message.pinned = True
    await chat_history.add_message(history_message)
    return True


async def count_usage(
    message: core.TelegramMessage, results: chatgpt.messages.ModelMessage
):
    token_usage = results.prompt_tokens + results.reply_tokens
    usage_cost = results.cost

    user_metrics = await metrics.TelegramMetrics(
        entity_id=str(message.user.id)
    ).load()
    user_metrics.usage += token_usage
    user_metrics.usage_cost += usage_cost
    await user_metrics.save()

    chat_metrics = await metrics.TelegramMetrics(
        entity_id=message.chat_id
    ).load()
    chat_metrics.usage += token_usage
    chat_metrics.usage_cost += usage_cost
    await chat_metrics.save()


async def get_usage(user_id: int | str, chat_id: int | str):
    user_metrics = await metrics.TelegramMetrics(entity_id=str(user_id)).load()
    chat_metrics = await metrics.TelegramMetrics(entity_id=str(chat_id)).load()
    return user_metrics, chat_metrics


async def get_config(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return chat_model


async def set_config(
    message: core.TelegramMessage, config: chatgpt.core.ModelConfig
):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.set_model(config)


async def set_model(message: core.TelegramMessage, model_name: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.chat_model = chatgpt.core.ModelConfig.model(model_name)
    await chat_history.set_model(chat_model)


async def toggle_tool(message: core.TelegramMessage, tool: chatgpt.tools.Tool):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    for t in chat_model.tools:
        # disable the tool if enabled
        if t.name == tool.name:
            chat_model.tools.remove(t)
            await chat_history.set_model(chat_model)
            return False
    # enable the tool if disabled
    chat_model.tools.append(tool)
    await chat_history.set_model(chat_model)
    return True


async def has_tool(message: core.TelegramMessage, tool: chatgpt.tools.Tool):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return tool.name in [t.name for t in chat_model.tools]


async def get_tools(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return chat_model.tools


async def set_prompt(message: core.TelegramMessage, prompt: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.prompt = chatgpt.messages.SystemMessage(prompt)
    await chat_history.set_model(chat_model)


async def set_temp(message: core.TelegramMessage, temp: float):
    if not (0 <= temp <= 2):
        raise ValueError("Temperature must be between 0 and 2.")
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.temperature = temp
    await chat_history.set_model(chat_model)


async def toggle_streaming(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.streaming = not chat_model.streaming
    await chat_history.set_model(chat_model)
    return chat_model.streaming


async def toggle_reply_mode(chat_id: int | str):
    chat_metrics = await metrics.TelegramMetrics(entity_id=str(chat_id)).load()
    chat_metrics.reply_to_mentions = not chat_metrics.reply_to_mentions
    await chat_metrics.save()
    return chat_metrics.reply_to_mentions


async def toggle_message_deletion(chat_id: int | str):
    chat_metrics = await metrics.TelegramMetrics(entity_id=str(chat_id)).load()
    chat_metrics.delete_messages = not chat_metrics.delete_messages
    await chat_metrics.save()
    return chat_metrics.delete_messages


async def clean_memory(memory: chatgpt.memory.ChatMemory, chat_id: int):
    for message in await memory.history.messages:
        try:  # check if message was sent to user
            message_id = int(message.id)
        except ValueError:
            continue
        # delete from model memory if deleted from telegram
        if await telegram_utils.is_deleted(chat_id, message_id):
            logger.debug(f"Deleting message:\n{message.serialize()}")
            await memory.history.delete_message(message.id)
