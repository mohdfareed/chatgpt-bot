"""Chat messages handler. Handles model generated replies and streams."""

import telegram.constants

import bot.formatter as formatter
import bot.models
import chatgpt.core
import chatgpt.events
import chatgpt.memory
import chatgpt.model
import chatgpt.openai.supported_models

TOOL_USAGE_MESSAGE = """
```
Using tool:
{tool_name}

With options:
{args_str}
```
""".strip()

PARSE_MODE = telegram.constants.ParseMode.HTML


class ModelMessageHandler(
    chatgpt.events.ModelRun,
    chatgpt.events.ModelStart,
    chatgpt.events.ModelGeneration,
    chatgpt.events.ModelEnd,
    chatgpt.events.ToolUse,
    chatgpt.events.ToolResult,
    chatgpt.events.ModelReply,
    chatgpt.events.ModelInterrupt,
    chatgpt.events.ModelError,
):
    """Handles model generated replies."""

    CHUNK_SIZE = 10
    """The number of packets to send at once."""

    def __init__(self, message: bot.models.TextMessage):
        self.user_message = message
        """The user message to which the model is replying."""

    async def on_model_run(self, _):
        # set typing status
        await self.user_message.telegram_message.chat.send_action("typing")

    async def on_model_start(self, config, context, tools):
        # set typing status
        # await self.user_message.telegram_message.chat.send_action("typing")
        # set handler states
        self.counter = 0  # the accumulated packets counter
        self.last_message = ""  # the last message sent
        self.reply = None  # the model's reply message

    async def on_model_generation(self, packet, aggregator):
        if not aggregator or not aggregator.reply:
            return  # don't send packets if none are available
        # wait for chunks to accumulate
        if self.counter < self.CHUNK_SIZE:
            self.counter += 1
            return  # don't send packets if the counter is not full

        # send packet
        await self._send_packet(aggregator.reply)
        self.counter = 0  # reset counter

    async def on_model_end(self, message):
        # send remaining packets or new message (if not streaming)
        if not self.reply or self.counter > 0:
            await self._send_packet(message)
        # set the usage's message ID
        message.id = str(self.reply.message_id)

    async def on_tool_use(self, usage):
        pass

    async def on_tool_result(self, results):
        # send results as a reply to the model's reply
        await self.reply.reply_html(f"<code>{results.content}</code>")

    async def on_model_reply(self, reply):
        pass

    async def on_model_error(self, _):
        pass

    async def on_model_interrupt(self):
        pass

    async def _send_packet(self, new_message: chatgpt.core.ModelMessage):
        message = _create_message(new_message)  # parse message
        if message == self.last_message:
            return  # don't send empty packets

        # send new message if no reply has been sent yet
        if not self.reply:
            await self._create_reply(
                message, isinstance(new_message, chatgpt.core.ToolUsage)
            )
        else:  # edit the existing reply otherwise
            await self.reply.reply_html(message)
        # update last message
        self.last_message = message

    async def _create_reply(self, new_message: str, tool_usage=False):
        # send message without replying if using a tool
        if tool_usage:
            self.reply = (
                await self.user_message.chat.telegram_chat.send_message(
                    new_message, PARSE_MODE
                )
            )
        else:  # reply to the user otherwise
            self.reply = await self.user_message.telegram_message.reply_html(
                new_message
            )


# TODO: add metrics handler (extend existing handler to count usage)


async def generate_reply(
    message: bot.models.TextMessage,
):
    """Generates a reply for the given message."""
    # the chat model model
    model = chatgpt.openai.supported_models.CHATGPT
    # create handler
    message_handler = ModelMessageHandler(message)
    # initialize model's memory
    memory = await chatgpt.memory.ChatMemory.initialize(
        message.chat_id, 3500, 2500
    )
    # setup the model
    model = chatgpt.model.ChatModel(
        memory=memory,
        handlers=[message_handler],
    )
    # generate a reply
    return await model.run(message.to_chat_message())


def _create_message(message: chatgpt.core.ModelMessage) -> str:
    if isinstance(message, chatgpt.core.ToolUsage):
        return formatter.md_html(_format_tool_usage(message))
    return formatter.md_html(message.content)


def _format_tool_usage(usage: chatgpt.core.ToolUsage) -> str:
    return TOOL_USAGE_MESSAGE.format(
        tool_name=usage.tool_name, args_str=usage.args_str[:1000]
    )
