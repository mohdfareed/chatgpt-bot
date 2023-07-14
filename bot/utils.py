"""Utilities and helper functions."""

import chatgpt.core
import chatgpt.memory
import chatgpt.messages
import chatgpt.model
import chatgpt.tools
from bot import chat_handler, core, formatter, metrics


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
    # setup the chat model
    model = chatgpt.model.ChatModel(
        memory=memory,
        handlers=[handler, metrics_handler],
    )

    return await model.run(message.to_chat_message())


async def add_message(message: core.TextMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.add_message(message.to_chat_message())


async def delete_message(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.delete_message(str(message.id))


async def delete_history(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.clear()


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


async def get_usage(message: core.TelegramMessage):
    user_metrics = await metrics.TelegramMetrics(
        entity_id=str(message.user.id)
    ).load()
    chat_metrics = await metrics.TelegramMetrics(
        entity_id=message.chat_id
    ).load()

    return (
        f"User tokens usage: {round(user_metrics.usage, 4)}\n"
        f"       usage cost: ${round(chat_metrics.usage_cost, 2)}\n"
        f"Chat tokens usage: {round(chat_metrics.usage, 4)}\n"
        f"       usage cost: ${round(chat_metrics.usage_cost, 2)}"
    )


async def set_temp(message: core.TelegramMessage, temp: float):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.temperature = temp
    await chat_history.set_model(chat_model)


async def set_prompt(message: core.TelegramMessage, prompt: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.prompt = chatgpt.messages.SystemMessage(prompt)
    await chat_history.set_model(chat_model)


async def load_config(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return _format_model(chat_model)


async def set_model(message: core.TelegramMessage, model_name: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.chat_model = chatgpt.core.ModelConfig.model(model_name)
    await chat_history.set_model(chat_model)


async def get_model(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return chat_model.chat_model


async def set_tools(
    message: core.TelegramMessage, tools: list[chatgpt.tools.Tool]
):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.tools = tools
    await chat_history.set_model(chat_model)


async def toggle_streaming(message: core.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.streaming = not chat_model.streaming
    await chat_history.set_model(chat_model)
    return chat_model.streaming


async def set_max_tokens(message: core.TelegramMessage, max: int):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.max_tokens = max
    await chat_history.set_model(chat_model)


def _format_model(config: chatgpt.core.ModelConfig):
    tools = [f"<code>{tool.name}</code>" for tool in config.tools]
    prompt = config.prompt or chatgpt.messages.SystemMessage("")
    return formatter.format_message(
        f"Name: <code>{config.chat_model.name}</code>\n"
        f"Size: <code>{config.chat_model.size} tokens</code>\n"
        f"Temperature: <code>{config.temperature}</code>\n"
        f"Input cost: <code>${config.chat_model.input_cost}/1k tokens</code>\n"
        f"Output cost: <code>${config.chat_model.output_cost}/1k tokens</code>\n"
        f"Streams messages: <code>{config.streaming}</code>\n"
        f"Tools: {', '.join(tools)}\n"
        f"System prompt: <code>{prompt.content}</code>"
    )
