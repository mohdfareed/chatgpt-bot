"""Utilities and helper functions."""

import bot.chat_handler
import bot.models
import chatgpt.core
import chatgpt.memory
import chatgpt.model
import chatgpt.tools

running_models: list[chatgpt.model.ChatModel] = []
"""A dictionary of running models."""


async def reply_to_user(message: bot.models.TextMessage, reply=False):
    """Reply to a user with a generated model reply."""
    # create handlers
    chat_handler = bot.chat_handler.ModelMessageHandler(message, reply=reply)
    metrics_handler = bot.chat_handler.ModelMetricsHandler(message)
    # initialize model's memory
    memory = await chatgpt.memory.ChatMemory.initialize(
        message.chat_id,
        summarization_handlers=[metrics_handler],
    )
    # setup the chat model
    model = chatgpt.model.ChatModel(
        memory=memory,
        handlers=[chat_handler, metrics_handler],
    )
    # generate a reply
    return await model.run(message.to_chat_message())


async def stop_model(message: bot.models.TelegramMessage, stop_all=False):
    """Stop the model from generating the message."""
    if stop_all:
        (  # stop all models in the chat
            await model.stop()
            for model in running_models
            if model.memory.history.chat_id == message.chat_id
        )
        return

    for model in running_models:  # find model
        for handler in model.events_manager.handlers:  # find telegram handler
            if type(handler) == bot.chat_handler.ModelMessageHandler:
                # if the reply the model is generating is the one to stop
                if handler.reply and handler.reply.id == message.id:
                    await model.stop()


async def reply_code(message: bot.models.TelegramMessage | None, reply):
    """Reply to a message with a code block."""
    if message:
        await message.telegram_message.reply_html(text=f"<code>{reply}</code>")


async def add_message(message: bot.models.TextMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.add_message(message.to_chat_message())


async def delete_message(message: bot.models.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.delete_message(str(message.id))


async def delete_history(message: bot.models.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    await chat_history.clear()


async def count_usage(
    message: bot.models.TelegramMessage, results: chatgpt.core.ModelMessage
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
        entity_id=message.chat_id
    ).load()
    chat_metrics.usage += token_usage
    chat_metrics.usage_cost += usage_cost
    await chat_metrics.save()


async def get_usage(message: bot.models.TelegramMessage):
    user_metrics = await bot.models.TelegramMetrics(
        entity_id=str(message.user.id)
    ).load()
    chat_metrics = await bot.models.TelegramMetrics(
        entity_id=message.chat_id
    ).load()

    return (
        f"User tokens usage: ${round(user_metrics.usage, 4)}\n"
        f"       usage cost: {round(chat_metrics.usage_cost, 2)}\n"
        f"Chat tokens usage: ${round(chat_metrics.usage, 4)}\n"
        f"       usage cost: {round(chat_metrics.usage_cost, 2)}"
    )


async def load_config(message: bot.models.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    return _format_model(chat_model)


async def set_model(message: bot.models.TelegramMessage, model_name: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.chat_model = chatgpt.core.ModelConfig.model(model_name)
    await chat_history.set_model(chat_model)


async def set_tools(
    message: bot.models.TelegramMessage, tools: list[chatgpt.tools.Tool]
):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.tools = tools
    await chat_history.set_model(chat_model)


async def set_prompt(message: bot.models.TelegramMessage, prompt: str):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.prompt = chatgpt.core.SystemMessage(prompt)
    await chat_history.set_model(chat_model)


async def set_temp(message: bot.models.TelegramMessage, temp: float):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.temperature = temp
    await chat_history.set_model(chat_model)


async def toggle_streaming(message: bot.models.TelegramMessage):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.streaming = not chat_model.streaming
    await chat_history.set_model(chat_model)
    return chat_model.streaming


async def set_max_tokens(message: bot.models.TelegramMessage, max: int):
    chat_history = await chatgpt.memory.ChatHistory.initialize(message.chat_id)
    chat_model = await chat_history.model
    chat_model.max_tokens = max
    await chat_history.set_model(chat_model)


def _format_model(config: chatgpt.core.ModelConfig):
    tools = [f"<code>{tool.name}</code>" for tool in config.tools]
    return (
        f"Name: <code>{config.chat_model.name}</code>\n"
        f"Size: <code>{config.chat_model.size} tokens</code>\n"
        f"Temperature: <code>{config.temperature}</code>\n"
        f"Input cost: <code>${config.chat_model.input_cost}/1k tokens</code>\n"
        f"Output cost: <code>${config.chat_model.output_cost}/1k tokens</code>\n"
        f"Streams messages: <code>{config.streaming}</code>\n"
        f"Tools: {', '.join(tools)}\n"
        f"System prompt: <code>{config.prompt or ''}</code>"
    )
